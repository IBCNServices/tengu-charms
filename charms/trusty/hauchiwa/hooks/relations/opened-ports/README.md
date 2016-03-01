# port-forwarding relationship

The provides side puts all its open ports on the relationship. The requires side configures port forwards to the given ports.

# How to use


## Provides

    @when('hauchiwa.available')
    def configure_port_forward(port_forward):
        port_forward.configure()

## Requires

    @when_all('opened-ports.available')
    def configure_port_forwards(relation):
        services = relation.opened_ports
        update_port_forwards(services)
