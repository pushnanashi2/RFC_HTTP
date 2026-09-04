import express from "express";

const router = express.Router();

function createJob() {
  router.post("/jobs", (_request, response) => {
    response.status(202).json({ job_id: "job_123" });
  });
}

function jobStatus() {
  router.get("/jobs/:jobId/status", (_request, response) => {
    response.status(200).json({ state: "running", progress: 20 });
  });
}

function cancelJob() {
  router.post("/jobs/:jobId/cancel", (_request, response) => {
    response.status(202).json({ state: "cancelled" });
  });
}

export { router, createJob, jobStatus, cancelJob };
