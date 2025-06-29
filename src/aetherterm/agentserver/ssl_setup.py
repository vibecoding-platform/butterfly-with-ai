#!/usr/bin/env python3
"""
SSL Certificate Setup CLI for AetherTerm AgentServer

This module provides a standalone CLI command for generating SSL certificates
needed for secure HTTPS operation of the AetherTerm AgentServer.
"""

import logging
import os
import sys
from pathlib import Path

import click

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("aetherterm.ssl_setup")


@click.command()
@click.option(
    "--host",
    default="localhost",
    help="Hostname for SSL certificate generation.",
    show_default=True,
)
@click.option(
    "--port",
    default=57575,
    type=int,
    help="Port number for the server (informational only).",
    show_default=True,
)
@click.option(
    "--cert-dir",
    default=None,
    help="Directory to store SSL certificates (defaults to ~/.aetherterm/ssl).",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force regeneration of certificates even if they exist.",
)
@click.option(
    "--key-size",
    default=2048,
    type=int,
    help="RSA key size for certificate generation.",
    show_default=True,
)
@click.option(
    "--days",
    default=365,
    type=int,
    help="Certificate validity period in days.",
    show_default=True,
)
def main(host, port, cert_dir, force, key_size, days):
    """
    Generate SSL certificates for AetherTerm AgentServer.

    This command creates self-signed SSL certificates that can be used
    for secure HTTPS operation of the AetherTerm AgentServer.

    Examples:
        aetherterm-ssl-setup
        aetherterm-ssl-setup --host=myserver.local --port=8443
        aetherterm-ssl-setup --cert-dir=/etc/aetherterm/ssl --force
    """
    log.info("AetherTerm SSL Certificate Setup")
    log.info(f"Hostname: {host}")
    log.info(f"Server port: {port}")

    # Determine certificate directory
    if cert_dir is None:
        home_dir = Path.home()
        cert_dir = home_dir / ".aetherterm" / "ssl"
    else:
        cert_dir = Path(cert_dir)

    log.info(f"Certificate directory: {cert_dir}")

    # Create directory if it doesn't exist
    cert_dir.mkdir(parents=True, exist_ok=True)

    # Certificate file paths
    cert_file = cert_dir / "aetherterm.crt"
    key_file = cert_dir / "aetherterm.key"

    # Check if certificates already exist
    if cert_file.exists() and key_file.exists() and not force:
        log.info("SSL certificates already exist!")
        log.info(f"Certificate: {cert_file}")
        log.info(f"Private key: {key_file}")
        log.info("Use --force to regenerate certificates")
        return

    # Import the SSL certificate generation function
    try:
        from aetherterm.agentserver.utils.ssl_certs import prepare_ssl_certs
    except ImportError as e:
        log.error("SSL certificate generation not available")
        log.error(f"Import error: {e}")
        log.error("Please ensure all dependencies are installed")
        sys.exit(1)

    # Prepare certificate generation arguments
    kwargs = {
        "host": host,
        "port": port,
        "cert_dir": str(cert_dir),
        "force": force,
        "key_size": key_size,
        "days": days,
    }

    try:
        log.info("Generating SSL certificates...")
        prepare_ssl_certs(**kwargs)

        # Verify certificates were created
        if cert_file.exists() and key_file.exists():
            log.info("✅ SSL certificates generated successfully!")
            log.info(f"📄 Certificate: {cert_file}")
            log.info(f"🔑 Private key: {key_file}")
            log.info("")
            log.info("🚀 You can now start AetherTerm AgentServer with HTTPS:")
            log.info(f"   aetherterm-agentserver --host={host} --port={port}")
            log.info("")
            log.info("⚠️  Note: These are self-signed certificates.")
            log.info("   Your browser will show a security warning on first access.")
        else:
            log.error("❌ Certificate generation failed - files not found")
            sys.exit(1)

    except Exception as e:
        log.error(f"❌ Certificate generation failed: {e}")
        log.error("Please check the error message and try again")
        sys.exit(1)


if __name__ == "__main__":
    main()
