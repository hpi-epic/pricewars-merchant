###
# Merchant A / Cheapest
##

role :www, %w(deployer@tunnel.framsteg.de)
server "tunnel.framsteg.de", user: "deployer", roles: %w(www)

# uncomment in case of travis, capistrano will have its own
set :ssh_options, keys: ["config/id_rsa"] if File.exist?("config/id_rsa")
set :ssh_options, port: 7047
set :api_token, "TanxeiJnQPRPBM7ov5PKcmZ1ik1h5pCZQ0X5jqsAFKZRgfGckfwNSWOBHPsNF4vf"
set :deploy_to, "/var/www/pricewars-merchant3"

after :deploy, "deploy:activate_merchant_a"
