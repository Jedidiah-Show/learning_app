# Release Process

## Pre-deployment
- Run tests in clean environment
- Run linting/checks
- Verify migrations
- Check secrets/config

## Deployment
- Apply migrations
- Deploy app
- Run smoke tests
- Verify health endpoints

## Rollback
- Revert to previous commit
- Rollback migrations if needed
- Verify health

## Monitoring
- Check /healthz, /readyz
- Monitor logs

## Health Checks
- `/healthz` - basic health
- `/readyz` - readiness with database/migrations

## Rollback Procedure
1. Identify last known good commit
2. Revert deployment to previous version
3. If migrations need rollback, run `flask db downgrade` carefully
4. Verify health endpoints
5. Document incident
