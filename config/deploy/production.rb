role :www, %w(deployer@tunnel.framsteg.de)
server "tunnel.framsteg.de", user: "deployer", roles: %w(www)

# uncomment in case of travis, capistrano will have its own
set :ssh_options, keys: ["config/deploy_id_rsa"] if File.exist?("config/deploy_id_rsa")
set :ssh_options, port: 7047
set :api_token, "AbSn3B7xZe1imvJPRbow2w4lcRIrKtJTVlIYvPXW4XFrTYHuA6rC2wxeNGWhApBf"
set :deploy_to, "/var/www/pricewars-merchant"
