# Buildar

Buildar configuration is sort of a shit show.

AWS_DEFAULT_REGION will be the build region

--vpc will default to the default VPC in us-east-1 so just build there.

You must set BASTION_VPN_PASSWORD in the environment and it must correspond to
the bastion_id in buildar.yaml.

Once you have this ridiculous nonsense figured out, go ahead and run:

`./buildar.py`

And the rest is automated. I optimized for making the actual fucking build work
instead of making it easy to use. Sorry, not sorry. If someone wants to make it
easier to use, I'd very much appreciate that. Just open a PR and update the
docs.

When this is all done, you'll have a new AMI in all of the regions. After that
there are a couple of Lambda tasks that are going to come around and make it
public.

See https://github.com/opsee/lacroix for the source to those lambda tasks. They
are setup to run in us-west-2.
