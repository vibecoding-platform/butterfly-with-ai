# ARM64 Support Documentation

## Overview
AetherTerm now includes comprehensive ARM64 architecture support, enabling deployment on Apple Silicon Macs, AWS Graviton instances, and Raspberry Pi devices.

## Implementation Status

### ✅ Completed
- **Ruff Configuration**: Python linting and formatting with 100-char line length
- **Pre-commit Hooks**: Code quality enforcement with file exclusions
- **GitHub Actions CI/CD**: Multi-architecture testing pipeline
- **Python Compatibility**: Testing across Python 3.9-3.12
- **Dependency Management**: Simplified psycopg2 handling for cross-platform support
- **Jupyter Integration**: Optional jupyter-server-proxy support

### 🚧 Known Issues
1. **Docker ARM64 Builds**: Currently experiencing build failures in CI
2. **Pre-commit Hooks**: Still modifying some documentation files
3. **macOS Python 3.9/3.10**: Library compatibility issues on GitHub runners

## Configuration Files

### ruff.toml
```toml
line-length = 100
target-version = "py39"

[lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ARG", "COM", "DTZ", "ANN", "S", "T20", "PIE", "RET", "SLF", "RSE", "ERA", "PTH", "PL", "TRY", "NPY", "PERF"]
ignore = ["E501", "B008", "C901", "ANN101", "ANN102", "ANN401", "S101", "S104", "S608", "TRY003", "PLR0913", "UP006", "UP007"]
```

### .github/workflows/ci.yml
- Multi-platform matrix testing (Ubuntu, macOS)
- Python versions 3.9-3.12 (excluding 3.9/3.10 on macOS)
- Docker multi-architecture builds
- Security scanning with Bandit
- Frontend build validation

### pyproject.toml Updates
- Removed ARM64-specific dependency group
- Simplified psycopg2 to use psycopg2-binary for all platforms
- Added optional Jupyter integration dependencies

## Usage

### Local Development
```bash
# Install dependencies
make install

# Run tests
pytest

# Lint code
make lint

# Build frontend
make build-frontend
```

### Docker Multi-Architecture Build
```bash
# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t aetherterm:latest .
```

### Jupyter Integration
```bash
# Install with Jupyter support
pip install -e ".[jupyter]"

# Run setup script
bash scripts/setup_jupyter.sh
```

## Troubleshooting

### Common Issues

1. **psycopg2 Build Failures on ARM64**
   - Solution: Use psycopg2-binary instead of psycopg2
   - Already configured in pyproject.toml

2. **Pre-commit Hook Failures**
   - Solution: Run `pre-commit run --all-files` locally before committing
   - Documentation files are excluded from whitespace checks

3. **macOS Python Setup Failures**
   - Issue: Missing system libraries for Python 3.9/3.10
   - Solution: Use Python 3.11+ on macOS

## Future Improvements

1. Fix Docker ARM64 build issues in CI
2. Complete pre-commit hook configuration refinement
3. Add ARM64-specific performance optimizations
4. Expand test coverage for ARM64-specific features

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [GitHub Actions Multi-Architecture](https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners)
- [Docker Buildx](https://docs.docker.com/buildx/working-with-buildx/)