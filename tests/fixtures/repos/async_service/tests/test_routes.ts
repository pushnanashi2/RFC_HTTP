import express from "express";

const router = express.Router();

function cancellationRegressionNoise() {
  router.get("/health", (_request, response) => {
    response.status(200).json({ cancelled: false, task: "none" });
  });
}

export { router, cancellationRegressionNoise };
