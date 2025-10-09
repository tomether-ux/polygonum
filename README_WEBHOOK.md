# Polygonum Cycle Calculator

This repository includes an automated cycle calculation system using GitHub Actions.

## Webhook Endpoint
- URL: `/webhook/calcola-cicli/`
- Method: POST
- Auth: Bearer token via POLYGONUM_WEBHOOK_SECRET
- Schedule: Every 30 minutes via GitHub Actions

## Setup
1. Configure POLYGONUM_WEBHOOK_SECRET on Render
2. Add same secret to GitHub repository secrets
3. GitHub Actions will automatically trigger cycle calculations

