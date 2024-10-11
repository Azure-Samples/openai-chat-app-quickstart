import argparse
import azure.core.exceptions
from azure.identity import DefaultAzureCredential
from azure.mgmt.cognitiveservices import CognitiveServicesManagementClient

# Set up argument parsing
parser = argparse.ArgumentParser(description="Delete an Azure OpenAI deployment.")
parser.add_argument("--resource-name", required=True, help="The name of the Azure OpenAI resource.")
parser.add_argument("--resource-group", required=True, help="The name of the Azure resource group.")
parser.add_argument("--deployment-name", required=True, help="The name of the deployment to delete.")
parser.add_argument("--subscription-id", required=True, help="The Azure subscription ID.")

print(f"Pre-down OpenAI script starting.")

args = parser.parse_args()

# Authenticate using DefaultAzureCredential
credential = DefaultAzureCredential()

# Initialize the Cognitive Services client
client = CognitiveServicesManagementClient(credential, subscription_id=args.subscription_id)
try:
    # Begin delete the deployment
    poller = client.deployments.begin_delete(
        resource_group_name=args.resource_group, account_name=args.resource_name, deployment_name=args.deployment_name
    )
except azure.core.exceptions.ResourceNotFoundError:
    print(f"Deployment {args.deployment_name} not found.")
    exit(0)

# Wait for the delete operation to complete
poller.result()

print(f"Deployment {args.deployment_name} deleted successfully.")
