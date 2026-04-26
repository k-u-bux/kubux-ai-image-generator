def generate_formats_xy ( min_x, max_x, delta_x, min_y, max_y, delta_y ):
    x_range = range( min_x, max_x+1, delta_x )
    y_range = range( min_y, max_y+1, delta_y )
    result = [ (x,y) for x in x_range for y in y_range ]
    return result

def generate_formats ( a, b, d ):
    return generate_formats_xy( a, b, d, a, b, d )

MODEL_SPECS = [
    # (Display Name, Model ID, available_formats, supports_steps, step_range, supports_image_url, supports_negative_prompt, supports_reference_strength)
    ("FLUX.1 Kontext [max]", "black-forest-labs/FLUX.1-kontext-max", generate_formats( 256, 1440, 32 ), True, (1, 50), True, False, True),
    ("FLUX.1 Kontext [pro]", "black-forest-labs/FLUX.1-kontext-pro", generate_formats( 256, 1440, 32 ), True, (1, 50), True, False, True),
    ("FLUX.1 Krea [dev]", "black-forest-labs/FLUX.1-krea-dev", generate_formats( 256, 1440, 32 ), True, (20, 50), True, False, True),
    ("FLUX.1 [pro]", "black-forest-labs/FLUX.1-pro", generate_formats( 256, 1440, 32 ), True, (15, 50), False, False, False),
    ("FLUX.1 Schnell", "black-forest-labs/FLUX.1-schnell", generate_formats( 256, 1440, 32 ), True, (1, 12), False, False, False),
    ("FLUX1.1 [pro]", "black-forest-labs/FLUX.1.1-pro", generate_formats( 256, 1440, 32 ), False, (1, 4), False, False, False),
    ("FLUX.2 [dev]", "black-forest-labs/FLUX.2-dev", generate_formats( 400, 2048, 32 ), False, (20, 50), True, False, True),
    ("FLUX.2 [flex]", "black-forest-labs/FLUX.2-flex", generate_formats( 400, 2048, 32 ), False, (15, 50), True, False, True),
    ("FLUX.2 [pro]", "black-forest-labs/FLUX.2-pro", generate_formats( 400, 2048, 16 ), False, (15, 50), True, False, True),
    ("FLUX.2 [max]", "black-forest-labs/FLUX.2-max", generate_formats( 400, 2048, 16 ), False, (15, 50), True, False, True),
    ("GPT 1.5", "openai/gpt-image-1.5", [ (1024,1024), (1536,1024), (1024,1536) ], False, (15, 50), True, False, True),
    ("ByteDance Seedream 3.0", "ByteDance-Seed/Seedream-3.0", [(1024, 1024), (864, 1152), (1152, 864), (1280, 720), (720, 1280), (832, 1248), (1248, 832), (1512, 648)], False, (20, 40), True, True, True),
    ("ByteDance Seedream 4.0", "ByteDance-Seed/Seedream-4.0", generate_formats( 512, 4096, 64 ), False, (20, 50), True, True, True),
    ("Gemini Flash Image 2.5 (Nano Banana)", "google/flash-image-2.5", [(1024, 1024), (1248, 832), (832, 1248), (1184, 864), (864, 1184), (896, 1152), (1152, 896), (768, 1344), (1344, 768), (1536, 672)], False, None, True, False, True),
    ("Gemini 3 (Nano Banana 2 Pro)", "google/gemini-3-pro-image", generate_formats( 256, 2048, 64 ), False, None, False, False, False),
    ("Google Imagen 4.0 Fast", "google/imagen-4.0-fast", [(1024, 1024), (2048, 2048), (768, 1408), (1536, 2816), (1408, 768), (2816, 1536), (896, 1280), (1792, 2560), (1280, 896), (2560, 1792)], False, None, False, False, False),
    ("Google Imagen 4.0 Preview", "google/imagen-4.0-preview", [(1024, 1024), (2048, 2048), (768, 1408), (1536, 2816), (1408, 768), (2816, 1536), (896, 1280), (1792, 2560), (1280, 896), (2560, 1792)], False, None, True, False, True),
    ("Google Imagen 4.0 Ultra", "google/imagen-4.0-ultra", [(1024, 1024), (2048, 2048), (768, 1408), (1536, 2816), (1408, 768), (2816, 1536), (896, 1280), (1792, 2560), (1280, 896), (2560, 1792)], False, None, True, False, True),
    ("HiDream-I1-Dev", "HiDream-ai/HiDream-I1-Dev", generate_formats( 512, 1024, 64 ), True, (20, 30), True, True, True),
    ("HiDream-I1-Fast", "HiDream-ai/HiDream-I1-Fast", generate_formats( 512, 1024, 64 ), True, (4, 12), False, True, False),
    ("HiDream-I1-Full", "HiDream-ai/HiDream-I1-Full", generate_formats( 512, 2048, 64 ), True, (30, 50), True, True, True),
    ("Ideogram 3.0", "ideogram/ideogram-3.0", [(1536, 512), (1536, 576), (1472, 576), (1408, 576), (1536, 640), (1472, 640), (1408, 640), (1344, 640), (1472, 704), (1408, 704), (1344, 704), (1280, 704), (1312, 736), (1344, 768), (1216, 704), (1280, 768), (1152, 704), (1280, 800), (1216, 768), (1248, 832), (1216, 832), (1088, 768), (1152, 832), (1152, 864), (1088, 832), (1152, 896), (1120, 896), (1024, 832), (1088, 896), (960, 832), (1024, 896), (1088, 960), (960, 896), (1024, 960), (1024, 1024), (960, 1024), (896, 960), (960, 1088), (896, 1024), (832, 960), (896, 1088), (832, 1024), (896, 1120), (896, 1152), (832, 1088), (864, 1152), (832, 1152), (768, 1088), (832, 1216), (832, 1248), (768, 1216), (800, 1280), (704, 1152), (768, 1280), (704, 1216), (768, 1344), (736, 1312), (704, 1280), (704, 1344), (704, 1408), (704, 1472), (640, 1344), (640, 1408), (640, 1472), (640, 1536), (576, 1408), (576, 1472), (576, 1536), (512, 1536)], False, None, True, True, True),
    ("Dreamshaper", "Lykon/DreamShaper", generate_formats( 128, 1024, 64 ), True, (20, 50), False, True, False),
    ("Qwen Image", "Qwen/Qwen-Image", generate_formats( 256, 1280, 32 ), True, (20, 40), True, True, True),
    ("Juggernaut Lightning Flux by RunDiffusion", "Rundiffusion/Juggernaut-Lightning-Flux", generate_formats( 512, 1024, 32 ), True, (1, 8), False, False, False),
    ("Juggernaut Pro Flux by RunDiffusion 1.0.0", "RunDiffusion/Juggernaut-pro-flux", generate_formats( 512, 1440, 32 ), True, (20, 50), False, False, False),
    ("Stable Diffusion 3", "stabilityai/stable-diffusion-3-medium", generate_formats( 512, 1024, 64 ), True, (20, 50), False, True, False),
    ("SD XL", "stabilityai/stable-diffusion-xl-base-1.0", generate_formats( 512, 1024, 8 ), True, (20, 50), False, True, False),
    ("Wan 2.6 Image", "Wan-AI/Wan2.6-image", generate_formats( 512, 2048, 32 ), False, (20, 50), True, True, True),
]

# end of file
