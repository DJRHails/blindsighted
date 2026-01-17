#!/bin/bash
# Generate self-signed SSL certificate for localhost

openssl req -x509 -newkey rsa:4096 \
  -keyout localhost-key.pem \
  -out localhost.pem \
  -days 365 \
  -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

echo "SSL certificates generated:"
echo "  - localhost-key.pem (private key)"
echo "  - localhost.pem (certificate)"
echo ""
echo "Note: You may need to accept the self-signed certificate in your browser."
