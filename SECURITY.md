# Security Policy

## Scope

This repository contains **static analysis documents**, **read-only analysis tools**, and **third-party binaries** redistributed unmodified for interoperability research. There is no service, no network endpoint, and no executable that the repository asks you to run against untrusted input.

## Reporting a vulnerability

If you find a security problem, please **open a private security advisory** on this repository (Security → Report a vulnerability) rather than a public issue.

Relevant categories:

| Category | Examples |
|---|---|
| **Tool defects with security impact** | A parsing bug in `tools/` that could be turned into memory corruption or arbitrary file write when run on a hostile input file |
| **Unexpected writes** | Any path where a `tools/` script writes outside a path you explicitly passed on the command line — the tools are intended to be strictly read-only apart from explicit output flags |
| **Credential exposure** | Any credential, token, or private key found in the repository history |
| **Content that should not be public** | Anything you believe is a copyright, licensing, or privacy problem — see also [`LEGAL.md`](../LEGAL.md) §6 |

## What is not in scope

- **Vulnerabilities in the third-party binaries themselves.** Those are redistributed unmodified; report them to their respective upstream projects. Their origins are listed in [`EXTERNAL_BINARIES.md`](../EXTERNAL_BINARIES.md).
- **Vulnerabilities in the analysed module.** This repository documents an existing public binary; it does not maintain it.
- **The fact that the repository contains third-party binaries.** That is a deliberate, documented part of the project — see [`LEGAL.md`](../LEGAL.md).

## Handling

- We will acknowledge a report as quickly as we can and will **not** require you to justify the report before we look at it.
- For anything that turns out to be a **rights-holder request**, we comply immediately and without argument — see [`LEGAL.md`](../LEGAL.md) §6.

## Safety notes for users

- The analysis tools are **read-only by design**. If you pass an output flag (`--out`, `--json`, `--hex-out`), the write goes to exactly the path you gave. Review the path before running.
- The third-party binaries are **not** covered by this repository's MIT license, and they are provided **as-is with no warranty**. Do not execute untrusted binaries; obtaining them from this repository does not imply they are safe to run.
- Hash values are published in [`EXTERNAL_BINARIES.md`](../EXTERNAL_BINARIES.md) precisely so you can **verify what you downloaded** before doing anything with it.
