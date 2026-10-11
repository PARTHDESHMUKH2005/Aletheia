import { beforeEach, test } from "node:test";
import assert from "node:assert/strict";
import { api, getToken, setToken } from "../src/api.js";

let calls;
beforeEach(() => {
  const values = new Map();
  globalThis.sessionStorage = {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
  calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ ok: true }), { headers: { "Content-Type": "application/json" } });
  };
});

test("organization uploads and saved routes carry credentials and item identity", async () => {
  setToken("credential-example");
  await api.createUploadTargets(2, "workshop", [100, 200]);
  assert.equal(calls[0].options.headers.get("Authorization"), "Bearer credential-example");
  assert.deepEqual(JSON.parse(calls[0].options.body), { count: 2, org_id: "workshop", sizes: [100, 200] });
  await api.saveRoute("stream", 1, 2, 0.3);
  assert.equal(calls[1].options.method, "PUT");
  assert.deepEqual(JSON.parse(calls[1].options.body), { w: 1, item_index: 2, evidence_weight: 0.3 });
});

test("presigned uploads do not disclose the API credential", async () => {
  setToken("private-credential");
  await api.putUpload("https://s3.example/photo.jpg?signature=example", new Blob(["photo"]));
  assert.equal(new Headers(calls[0].options.headers).has("Authorization"), false);
  assert.equal(new Headers(calls[0].options.headers).get("Content-Type"), "image/jpeg");
  assert.equal(new Headers(calls[0].options.headers).get("If-None-Match"), "*");
  await api.putUpload("/local-uploads/workshop/photo.jpg", new Blob(["photo"]));
  assert.equal(calls[1].options.headers.get("Authorization"), "Bearer private-credential");
});

test("sign-in uses the supplied credential and sign-out removes it", async () => {
  setToken("old-credential");
  await api.getSession("new-credential");
  assert.equal(calls[0].options.headers.get("Authorization"), "Bearer new-credential");
  setToken("");
  assert.equal(getToken(), "");
});

test("PDF responses remain binary and validation errors remain readable", async () => {
  globalThis.fetch = async () => new Response("%PDF-example", { headers: { "Content-Type": "application/pdf" } });
  const pdf = await api.getReport("stream");
  assert.equal(pdf.type, "application/pdf");
  assert.equal(await pdf.text(), "%PDF-example");
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: [{ msg: "bad weight" }] }), { status: 422 });
  await assert.rejects(api.advanceHandoff("stream", { status: "verified", weight_kg: -1 }), /bad weight/);
});

test("upload conflicts are surfaced for local and presigned targets", async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: "photo already uploaded" }), { status: 409 });
  await assert.rejects(api.putUpload("/local-uploads/workshop/photo.jpg", new Blob(["photo"])), /409 photo already uploaded/);
  globalThis.fetch = async () => new Response("PreconditionFailed", { status: 412 });
  await assert.rejects(api.putUpload("https://s3.example/photo.jpg?signature=example", new Blob(["photo"])), /Upload failed \(412\)/);
});
