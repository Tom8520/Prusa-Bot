import functools

from seleniumwire import webdriver  # Import from seleniumwire
import json
import discord
import datetime
from discord.ext import commands, tasks

from dotenv import load_dotenv
import os

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='p!', intents=intents)

def generate_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('headless')

    wire_options = {
        'disable_encoding': True  # Ask the server not to compress the response
    }

    return webdriver.Chrome(options=options, seleniumwire_options=wire_options)

products = [
    'original-prusa-mk4-kit-2',
    'original-prusa-mmu3-3',
    'original-prusa-xl-4',
    'original-prusa-i3-mk3s-kit-3',
    'original-prusa-mk4-2'
]


def get_product_data(product):
    driver = generate_driver()

    driver.scopes = [
        '.*graphql.*'
    ]

    driver.get(f'https://www.prusa3d.com/product/{product}/')

    for request in driver.requests:
        if request.response:
            if "graphql" in request.url:
                try:
                    res = request.response

                    response_body = json.loads(res.body.decode('utf-8'))
                    request_body = json.loads(request.body.decode('utf-8'))
                    status_code = request.response.status_code

                    if status_code == 200:
                        if request_body['operationName'] == 'getSingleProduct':
                            info = response_body['data']['product']

                            name = info['name']
                            in_stock = info['inStock']
                            preorder = info['isPreOrderProduct']
                            can_buy = not info['isSellingDenied']
                            extra = info['availability']['name']
                            price = info['price']['priceWithVat']

                            driver.close()

                            return name, in_stock, preorder, can_buy, extra, price
                except:
                    pass
    driver.close()
    return None

@bot.command()
async def getProduct(ctx, product: str):
    data = get_product_data(product)

    embed = discord.Embed(title=data [0])
    embed.add_field(name="In Stock", value=data [1])
    embed.add_field(name="Pre order", value=data[2])
    embed.add_field(name="Can buy", value=data[3])
    embed.add_field(name="Info", value=data[4])

    await ctx.send(embed=embed)

global product_id
product_id = 0

async def run_blocking(blocking_func, *args, **kwargs):
    """Runs a blocking function in a non-blocking way"""
    func = functools.partial(blocking_func, *args, **kwargs) # `run_in_executor` doesn't support kwargs, `functools.partial` does
    return await bot.loop.run_in_executor(None, func)

@tasks.loop(seconds=10)
async def update_product_details():
    global product_id
    with open('messages.json', 'r') as file:
        data = json.loads(file.read())

    CHANNEL_ID = 802837565182312460
    channel = bot.get_channel(CHANNEL_ID)

    product = products [product_id]

    product_data = await run_blocking(get_product_data, product)

    embed = discord.Embed(title=product_data[0], color=0xfc6d09)
    embed.add_field(name="In Stock", value=product_data[1])
    embed.add_field(name="Pre order", value=product_data[2])
    embed.add_field(name="Can buy", value=product_data[3])
    embed.add_field(name="Price", value=f"£{product_data [5]}")
    embed.add_field(name="Info", value=product_data[4])
    embed.set_footer(text=f"Last updated at {datetime.datetime.now()}")

    if product in data.keys():
        message_id = data [product]
        message = await channel.fetch_message(message_id)

        prev = message.embeds [0].fields [2].value

        if prev == 'False' and product_data [3]:
            USER_ID = 592409615568863232
            for x in range(5):
                await channel.send(f"<@{USER_ID}> {product} is in stock!!!!")

        await message.edit(embed=embed)
    else:
        message = await channel.send(embed=embed)
        data [product] = message.id

    product_id = (product_id + 1) % len(products)

    with open('messages.json', 'w') as file:
        file.write(json.dumps(data))

@bot.event
async def on_ready():
    update_product_details.start()

bot.run(os.environ ['TOKEN'])
