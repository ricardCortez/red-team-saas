/**
 * Red Team SaaS — TypeScript SDK usage example.
 *
 * This example assumes the SDK has been generated from the OpenAPI spec:
 *     npx openapi-ts --input http://localhost:8000/api/openapi.json --output ./typescript-sdk
 *
 * Alternatively, you can use fetch directly as shown below.
 */

const BASE_URL = "http://localhost:8000/api/v1";
const JWT_TOKEN = "eyJhbGciOiJIUzI1NiIs...your_token_here";

const headers = {
  Authorization: `Bearer ${JWT_TOKEN}`,
  "Content-Type": "application/json",
};

async function createProject(): Promise<Record<string, unknown>> {
  const resp = await fetch(`${BASE_URL}/projects`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      name: "Q1 External Audit",
      description: "Quarterly external penetration test",
    }),
  });
  if (!resp.ok) throw new Error(`Create project failed: ${resp.status}`);
  const project = await resp.json();
  console.log(`Created project: ${project.id} — ${project.name}`);
  return project;
}

async function listFindings(projectId: number): Promise<unknown[]> {
  const resp = await fetch(
    `${BASE_URL}/findings?project_id=${projectId}`,
    { headers },
  );
  if (!resp.ok) throw new Error(`List findings failed: ${resp.status}`);
  const findings = await resp.json();
  console.log(`Found ${findings.length} findings`);
  for (const f of findings) {
    console.log(`  [${f.severity ?? "N/A"}] ${f.title ?? "Untitled"}`);
  }
  return findings;
}

async function generateReport(projectId: number): Promise<Record<string, unknown>> {
  const resp = await fetch(`${BASE_URL}/reports`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      project_id: projectId,
      format: "pdf",
      template: "executive_summary",
    }),
  });
  if (!resp.ok) throw new Error(`Generate report failed: ${resp.status}`);
  const report = await resp.json();
  console.log(`Report queued: ${report.id}`);
  return report;
}

(async () => {
  const project = await createProject();
  await listFindings(project.id as number);
  await generateReport(project.id as number);
})();
