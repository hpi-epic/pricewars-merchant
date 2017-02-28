###
# Merchant F / MachineLearningMerchantApp
##

role :www, %w(deployer@tunnel.framsteg.de)
server "tunnel.framsteg.de", user: "deployer", roles: %w(www)

# uncomment in case of travis, capistrano will have its own
set :ssh_options, keys: ["config/id_rsa"] if File.exist?("config/id_rsa")
set :ssh_options, port: 7047
set :api_token, "fbfHqbVBvGvcJTRBqvYgAUAlO6iSXlvDNbUEDzP9GLlZoCjf8INInX4CdmeBYaOw"
set :deploy_to, "/var/www/pricewars-merchant7"

after :deploy, "deploy:activate_merchant_f"
