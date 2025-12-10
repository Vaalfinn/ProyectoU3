// PayFlow MX - Transaction Validator
// Script de Prueba de Estrés con k6
// Simula condiciones extremas y picos de tráfico

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

// Métricas personalizadas
const errorRate = new Rate("errors");
const validationDuration = new Trend("validation_duration");

// Configuración de prueba de estrés
export const options = {
  stages: [
    { duration: "1m", target: 100 }, // Warm-up
    { duration: "2m", target: 200 }, // Incremento moderado
    { duration: "2m", target: 400 }, // Incremento fuerte
    { duration: "3m", target: 600 }, // Estrés alto
    { duration: "2m", target: 800 }, // Estrés muy alto
    { duration: "3m", target: 1000 }, // Pico máximo
    { duration: "2m", target: 500 }, // Reducción gradual
    { duration: "2m", target: 0 }, // Cool-down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500", "p(99)<1000"],
    http_req_failed: ["rate<0.05"], // Más permisivo en prueba de estrés
    errors: ["rate<0.05"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

function generateTransaction() {
  const id = `STRESS-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
  const amount = Math.floor(Math.random() * 500000) + 100;

  return {
    transaction_id: id,
    amount: amount,
    currency: "MXN",
    sender_account: `ACC${Math.floor(Math.random() * 1000000000)}`,
    receiver_account: `ACC${Math.floor(Math.random() * 1000000000)}`,
    description: `Stress test transaction ${id}`,
  };
}

export default function () {
  const transaction = generateTransaction();
  const payload = JSON.stringify(transaction);
  const params = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const start = Date.now();
  const res = http.post(`${BASE_URL}/api/v1/validate`, payload, params);
  const duration = Date.now() - start;

  validationDuration.add(duration);

  const success = check(res, {
    "status is 200 or 500": (r) => r.status === 200 || r.status === 500,
    "response time < 2s": (r) => r.timings.duration < 2000,
  });

  if (!success) {
    errorRate.add(1);
    console.log(
      `Error: Status ${res.status}, Duration ${res.timings.duration}ms`
    );
  }

  // Mínimo tiempo de espera en prueba de estrés
  sleep(0.1);
}
