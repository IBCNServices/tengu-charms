from jinja2 import Environment, PackageLoader
env = Environment(loader=PackageLoader('bundletools', 'templates'))


def create_lambda(hnodes, snodes):
    template = env.get_template('lambda-bundle.yaml')
    return template.render(
        hnodes=hnodes,
        snodes=snodes,
    )
