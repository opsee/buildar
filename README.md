# Buildar

## Configuration

The following environment variables must be set in order to build an AMI:

`BUILDAR_REGION` - The region where buildar will build the AMI and launch the
test bastion.

`BUILDAR_VPC` - The VPC the build will happen in. This will be the default VPC
for the region if none is specified.

`BUILDAR_CUSTOMER_EMAIL` - The customer e-mail address / username associated
with the build account.

`BUILDAR_CUSTOMER_ID` - The customer ID associated with the user.

`BUILDAR_BASTION_ID` - The build bastion ID -- this must exist in keelhaul

`BUILDAR_VPN_PASSWORD` - The VPN password for the build bastion.

`BUILDAR_BASTION_VERSION` - This is a version associated with the bastion. It
is used for tagging the AMI only and has no impact on the actual software
version used.

All of these are also available as CLI flags:
`--region`
`--vpc`
`--customer-email`
`--customer-id`
`--bastion-id`
`--vpn-password`

Without all of this, you cannot launch a bastion--and the final step of the
bastion build process is to launch a bastion with the AMI you just built.

## buildar.yaml

The buildar configuration file, `buildar.yaml`, serves as a manifest for
everything on the bastion.

### Units

Each unit listed here must have a corresponding unit file or template in the
`units/` directory under buildar. The unit templates accept the variables
`image` and `version`.  If you need help with the templating language, see the
Jinja2 docs. If you specify a container image, you _must_ also specify a
corresponding version. There is no validation of buildar.yaml at the moment,
sadly, so you will end up running into a build failure very far into the build
process.

Unit templates will be rendered and placed into /etc/systemd/system on the
build host. The units will then be enabled once all units are in place. This
removes any ordering dependency so don't worry about those too much.

### Files

Files in the `files/` directory are copied to the Bastion and placed in
`remote_path`. You may specify `user`, `group`, and `mode` (in octal)
attributes. Once placed on the bastion the md5sum of the local and remote file
are compared ensuring consistency.

## Usage

To run a build, test the bastion, and publish the built AMI after its tests
pass, simply run: `./buildar.py --publish`. If you would like to keep the
artifacts of the build around, you can also pass it the `--no-cleanup` flag.
It will output the build_context used during the build so you can use the
buildar components to re-run parts of the steps if you want--including
automating your cleanup when you're finished.

After publishing your AMI to the build region, Lacroix lambda tasks will
come and mark the AMI as public and ensure that we only have a fixed number
of available AMIs in each region.

See https://github.com/opsee/lacroix for the source to those lambda tasks. They
are setup to run in us-west-2.
