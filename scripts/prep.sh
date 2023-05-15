 #!/bin/sh

echo "Copying azd environment variables to .env file"

azd env get-values > .env