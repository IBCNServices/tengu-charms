# docker-image-host relationship

The provides side retrieves all necessary information to run the docker image 
provided at the image parameter. Currently, nothing specific happens at 
the requiring side.

# How to use


## Provides

    @when_all('image.available')
    def run_images(relation):
        images = relation.images
        if images:
            for image in images:
                run_image(image)

## Requires

    @when('image.joined')
    def download_image(relation):
        image = start_downloading_image()
        relation.send_configuration(image, 'image1')
