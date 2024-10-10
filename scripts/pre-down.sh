#!/bin/bash

# Get the directory of the current script
script_dir=$(dirname "$0")

# Load environment variables from azd env
subscription_id=$(azd env get-value AZURE_SUBSCRIPTION_ID)
resource_name=$(azd env get-value AZURE_OPENAI_RESOURCE_NAME)
resource_group=$(azd env get-value AZURE_RESOURCE_GROUP)
deployment_name=$(azd env get-value AZURE_OPENAI_CHATGPT_DEPLOYMENT)

# Run the Python script with the retrieved values
python "$script_dir/pre-down.py" --subscription-id $subscription_id --resource-name $resource_name --resource-group $resource_group --deployment-name $deployment_name