
class Patch(object):

    def apply(self, request=None, reply=None):
        raise NotImplementedError()


class Destination(object):

    EXCHANGE = 'exchange'
    ROUTING_KEY = 'routing_key'

    @staticmethod
    def build(address):
        destination = None
        if address:
            exchange = None
            part = address.split('/', 1)
            if len(part) == 2:
                exchange = part[0]
                routing_key = part[1]
            else:
                routing_key = part[0]
            destination = {
                Destination.EXCHANGE: exchange,
                Destination.ROUTING_KEY: routing_key
            }
        return destination

    @staticmethod
    def address(destination):
        address = None
        if destination:
            if destination[Destination.EXCHANGE]:
                address = '%(exchange)s/%(routing_key)s' % destination
            else:
                address = destination[Destination.ROUTING_KEY]
        return address


class Patch2005(Patch):

    def apply(self, request=None, reply=None):
        if request:
            request.window = None
            request.any = request.data
            request.routing = Destination.build(request.routing)
            request.replyto = Destination.build(request.replyto)
            return
        if reply:
            reply.any = reply.data
            return


class Patch0520(Patch):

    def apply(self, request=None, reply=None):
        if request:
            request.data = request.any
            request.routing = Destination.address(request.routing)
            request.replyto = Destination.address(request.replyto)
            return
        if reply:
            reply.data = reply.any
            return


class Patcher(object):

    PATCHES = {
        ('2.0', '0.5'): Patch2005(),
        ('0.5', '2.0'): Patch0520(),
    }

    @staticmethod
    def patch(versions, request=None, reply=None):
        if versions[0] == versions[1]:
            # not needed
            return
        if not versions[1]:
            # not specified
            return
        patch = Patcher.PATCHES[versions]
        patch.apply(request, reply)
        request.version = versions[1]
