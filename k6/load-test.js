// PayFlow MX - Transaction Validator
// Script de Prueba de Carga con k6
// Simula tráfico normal de producción

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// Métricas personalizadas
const errorRate = new Rate("errors");
const validationDuration = new Trend("validation_duration");
const successfulValidations = new Counter("successful_validations");
const failedValidations = new Counter("failed_validations");

// Configuración de la prueba
export const options = {
  stages: [
    { duration: "2m", target: 50 }, // Ramp-up a 50 usuarios
    { duration: "5m", target: 50 }, // Mantener 50 usuarios
    { duration: "2m", target: 100 }, // Ramp-up a 100 usuarios
    { duration: "5m", target: 100 }, // Mantener 100 usuarios
    { duration: "2m", target: 150 }, // Pico de tráfico
    { duration: "3m", target: 150 }, // Mantener pico
    { duration: "2m", target: 0 }, // Ramp-down
  ],
  thresholds: {
    http_req_duration: ["p(95)<250", "p(99)<500"], // SLO de latencia
    http_req_failed: ["rate<0.001"], // SLO de errores < 0.1%
    errors: ["rate<0.001"],
    validation_duration: ["p(95)<250", "p(99)<500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// Generar datos de prueba
function generateTransaction() {
  const id = `TX-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  const amount = Math.floor(Math.random() * 100000) + 100;
  const currencies = ["MXN", "USD", "EUR"];

  return {
    transaction_id: id,
    amount: amount,
    currency: currencies[Math.floor(Math.random() * currencies.length)],
    sender_account: `ACC${Math.floor(Math.random() * 1000000000)}`,
    receiver_account: `ACC${Math.floor(Math.random() * 1000000000)}`,
    description: `Load test transaction ${id}`,
  };
}

export default function () {
  // Test 1: Health Check
  const healthRes = http.get(`${BASE_URL}/health`);
  check(healthRes, {
    "health check status 200": (r) => r.status === 200,
    "health check is healthy": (r) => JSON.parse(r.body).status === "healthy",
  });

  sleep(1);

  // Test 2: Validación de transacción
  const transaction = generateTransaction();
  const payload = JSON.stringify(transaction);
  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const start = Date.now();
  const validateRes = http.post(`${BASE_URL}/api/v1/validate`, payload, params);
  const duration = Date.now() - start;

  validationDuration.add(duration);

  const success = check(validateRes, {
    "validation status 200": (r) => r.status === 200,
    "validation has result": (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.transaction_id !== undefined;
      } catch (e) {
        return false;
      }
    },
    "validation latency < 500ms": (r) => r.timings.duration < 500,
  });

  if (success) {
    successfulValidations.add(1);
  } else {
    failedValidations.add(1);
    errorRate.add(1);
  }

  // Simular tiempo de pensamiento del usuario
  sleep(Math.random() * 3 + 1);

  // Test 3: Obtener stats (10% de las veces)
  if (Math.random() < 0.1) {
    const statsRes = http.get(`${BASE_URL}/api/v1/stats`);
    check(statsRes, {
      "stats status 200": (r) => r.status === 200,
    });
  }

  sleep(1);
}

export function handleSummary(data) {
  return {
    "k6/results/load-test-summary.json": JSON.stringify(data),
    stdout: textSummary(data, { indent: " ", enableColors: true }),
  };
}

function textSummary(data, options) {
  const indent = options.indent || "";
  const enableColors = options.enableColors || false;

  let summary = "\n";
  summary += indent + "==============================================\n";
  summary += indent + "  PayFlow MX - Load Test Summary\n";
  summary += indent + "==============================================\n\n";

  // Métricas HTTP
  summary += indent + "HTTP Metrics:\n";
  if (data.metrics.http_reqs) {
    summary +=
      indent + `  Total Requests: ${data.metrics.http_reqs.values.count}\n`;
  }
  if (data.metrics.http_req_duration) {
    summary +=
      indent +
      `  Latency P50: ${data.metrics.http_req_duration.values["p(50)"].toFixed(
        2
      )}ms\n`;
    summary +=
      indent +
      `  Latency P95: ${data.metrics.http_req_duration.values["p(95)"].toFixed(
        2
      )}ms\n`;
    summary +=
      indent +
      `  Latency P99: ${data.metrics.http_req_duration.values["p(99)"].toFixed(
        2
      )}ms\n`;
  }
  if (data.metrics.http_req_failed) {
    const failRate = (data.metrics.http_req_failed.values.rate * 100).toFixed(
      3
    );
    summary += indent + `  Error Rate: ${failRate}%\n`;
  }

  summary += "\n";
  summary += indent + "Custom Metrics:\n";
  if (data.metrics.successful_validations) {
    summary +=
      indent +
      `  Successful Validations: ${data.metrics.successful_validations.values.count}\n`;
  }
  if (data.metrics.failed_validations) {
    summary +=
      indent +
      `  Failed Validations: ${data.metrics.failed_validations.values.count}\n`;
  }

  summary += "\n";
  summary += indent + "SLO Compliance:\n";

  // Verificar SLOs
  if (data.metrics.http_req_duration) {
    const p95 = data.metrics.http_req_duration.values["p(95)"];
    const p99 = data.metrics.http_req_duration.values["p(99)"];
    summary +=
      indent +
      `  Latency P95 < 250ms: ${p95 < 250 ? "PASS ✓" : "FAIL ✗"} (${p95.toFixed(
        2
      )}ms)\n`;
    summary +=
      indent +
      `  Latency P99 < 500ms: ${p99 < 500 ? "PASS ✓" : "FAIL ✗"} (${p99.toFixed(
        2
      )}ms)\n`;
  }

  if (data.metrics.http_req_failed) {
    const errorRate = data.metrics.http_req_failed.values.rate;
    summary +=
      indent +
      `  Error Rate < 0.1%: ${errorRate < 0.001 ? "PASS ✓" : "FAIL ✗"} (${(
        errorRate * 100
      ).toFixed(3)}%)\n`;
  }

  summary += "\n";
  summary += indent + "==============================================\n";

  return summary;
}
