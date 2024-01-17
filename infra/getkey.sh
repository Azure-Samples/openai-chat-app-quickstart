if [ -z "$(az account show)" ]; then
    echo "You are not logged in. Please run 'az login' or 'az login --use-device-code' first."
    exit 1
fi

echo "Logged in, using this subscription:"
az account show --query "{subscriptionId:id, name:name}"
echo "If that is not the correct subscription, please run 'az account set --subscription \"<SUBSCRIPTION-NAME>\"'"

echo "Getting environment variables from .env file..."
openAiService=$(grep "AZURE_OPENAI_RESOURCE=" .env | cut -d '=' -f2 | tr -d '"')
resourceGroupName=$(grep "AZURE_OPENAI_RESOURCE_GROUP=" .env | cut -d '=' -f2  | tr -d '"')

echo "Getting OpenAI key from $openAiService in resourceGroup $resourceGroupName..."
openAiKey=$(az cognitiveservices account keys list --name $openAiService --resource-group $resourceGroupName --query key1 --output tsv)

echo "AZURE_OPENAI_KEY=\"$openAiKey\"" >> .env

echo "OpenAI key has been saved to .env file."
