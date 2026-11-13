# Security policy

## Supported versions

This repository is a 0.x source preview. Fixes land on `main`; older commits are not
patched separately.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting: open the **Security** tab and choose **Report a vulnerability**.
Include the affected commit or version, reproduction steps, and the impact you observed.
We will acknowledge the report, work on a fix, and coordinate disclosure with you.

You can also email [reports@kalanos.ai](mailto:reports@kalanos.ai). Email is not encrypted,
so use the GitHub advisory for sensitive technical detail.

Never include credentials, private reports or private datasets in a report.

## Scope

In scope: the code, examples and workflows in this repository, including what the adapters
choose to export. Issues in the Kalanos grader belong to
[KalanosAI/kalanos](https://github.com/KalanosAI/kalanos); tracker SDK issues belong to
their projects. For what the adapters send and what they leave to your tracker
configuration, read "Your data, your tracking destination" in the [README](README.md).
