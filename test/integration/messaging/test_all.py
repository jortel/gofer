import test_amqp
import test_proton
import test_qpid


def run():
    test_amqp.run()
    test_proton.run()
    test_qpid.run()

if __name__ == '__main__':
    run()