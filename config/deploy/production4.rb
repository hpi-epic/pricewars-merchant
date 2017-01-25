###
# Merchant E
##

role :www, %w(deployer@tunnel.framsteg.de)
server "tunnel.framsteg.de", user: "deployer", roles: %w(www)

# uncomment in case of travis, capistrano will have its own
set :ssh_options, keys: ["config/id_rsa"] if File.exist?("config/id_rsa")
set :ssh_options, port: 7047
set :api_token, "llhGt9Tao3YbN1ANPkI1QkDg3LC88EHt0xAu7dVvh4X45hSTSkVsVhZY3lgBzx60"
set :deploy_to, "/var/www/pricewars-merchant4"

after :deploy, "deploy:activate_merchant_e"
