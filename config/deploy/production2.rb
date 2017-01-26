###
# Merchant B / SecondCheapestMerchantApp
##

role :www, %w(deployer@tunnel.framsteg.de)
server "tunnel.framsteg.de", user: "deployer", roles: %w(www)

# uncomment in case of travis, capistrano will have its own
set :ssh_options, keys: ["config/deploy_id_rsa"] if File.exist?("config/deploy_id_rsa")
set :ssh_options, port: 7047
set :api_token, "bTEXsl4wJJomq5h1BaDEWCstSPbcGmIqFWO8IS5bltOcy6eBgrOD3H7Vgh8wUQnk"
set :deploy_to, "/var/www/pricewars-merchant2"

after :deploy, "deploy:activate_merchant_b"
