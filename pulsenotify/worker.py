import aioamqp
import logging
import os

log = logging.getLogger(__name__)

async def worker(consumer):
    try:
        transport, protocol = await aioamqp.connect(
            host=os.environ['PULSE_HOST'],
            login=os.environ['PULSE_LOGIN'],
            password=os.environ['PULSE_PASSWORD'],
            ssl=os.environ['PULSE_SSL'],
            port=os.environ['PULSE_PORT']
        )
    except aioamqp.AmqpClosedConnection as acc:
        log.exception('AMQP Connection closed: %s', acc)
        return

    channel = await protocol.channel()
    await channel.basic_qos(prefetch_count=1, prefetch_size=0,
                            connection_global=False)
    queue_name = 'queue/%s/%s' % (os.environ['PULSE_LOGIN'], os.environ['PULSE_QUEUE'],)
    log.info("Using queue: %s", queue_name)
    await channel.queue_declare(queue_name=queue_name, durable=True)
    for e in consumer.exchanges:
        log.info("Binding %s using %s", e, consumer.routing_key)
        await channel.queue_bind(exchange_name=e, queue_name=queue_name,
                                 routing_key=consumer.routing_key)
    await channel.basic_consume(consumer.dispatch, queue_name=queue_name)

    log.info('Worker has completed running.')
