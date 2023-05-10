#!/bin/sh
set -e

echo "Please enter your OpenAI API key found here: https://platform.openai.com/account/api-keys:"
read -r OPENAI_API_KEY

# Export the OPENAI_API_KEY environment variable
export OPENAI_API_KEY

./hostname-config.sh

echo "Click on GitHub Codespaces PORTS tab.  Right click on port 8000, and set Port Visibility to Public. Once Port 8000 if Public, press Enter to continue..."
read -r placeholder_var
