import aioamqp
import logging

log = logging.getLogger(__name__)


async def worker(config, consumer):
    try:
        transport, protocol = await aioamqp.connect(
            host=config["host"], login=config["login"],
            password=config["password"], ssl=config["ssl"],
            port=config["port"], heartbeat=1
        )
    except aioamqp.AmqpClosedConnection:
        log.warning("closed connections")
        return

    channel = await protocol.channel()
    await channel.basic_qos(prefetch_count=1, prefetch_size=0,
                            connection_global=False)
    queue_name = 'queue/%s/%s' % (config["login"], config["queue_name"],)
    log.info("Using queue: %s", queue_name)
    await channel.queue_declare(queue_name=queue_name, durable=False)
    for e in consumer.get_exchanges():
        log.info("binding %s using %s", e, consumer.routing_key)
        await channel.queue_bind(exchange_name=e, queue_name=queue_name,
                                 routing_key=consumer.routing_key)
    await channel.basic_consume(consumer.dispatch, queue_name=queue_name)
