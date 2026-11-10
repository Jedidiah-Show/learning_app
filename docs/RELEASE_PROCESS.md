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
