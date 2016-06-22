#!/usr/bin/env python

import click
from buildar.pipeline.pipeline import Pipeline, Tagger

@click.command()
@click.option('--image-name', help='Image name to manage.')
@click.option('--release-tag', help='Value to set for release tag.')
@click.option('--bastion-version', help='Bastion version.')
def tag(image_name, release_tag, bastion_version):
    build_context = {
        'release_tag': release_tag,
        'image_name': image_name,
        'build_region': 'us-east-1',
        'bastion_version': bastion_version,
    }

    build_pipeline = Pipeline()
    build_pipeline.add_step(Tagger())
    build_pipeline.execute(build_context)

if __name__ == '__main__':
    tag()
