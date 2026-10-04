"""Exercise the real packaged GUI and offline AI exports with synthetic fixtures."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.core import VERSION

build = json.loads((ROOT / f'delivery/build-result-{VERSION}.json').read_text(encoding='utf-8'))
exe = Path(build['executable'])
qa = ROOT / f'delivery/release-check-{build["platform"]}'; qa.mkdir(parents=True, exist_ok=True)
env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen', 'PYTHONIOENCODING': 'utf-8'}
gui_report = qa / 'gui.json'
subprocess.run([str(exe), '--check-gui', '--report', str(gui_report)], env=env, check=True, timeout=120)
gui = json.loads(gui_report.read_text(encoding='utf-8'))
assert gui['version'] == VERSION and gui['visible'] and gui['fit'] == 'image' and gui['dpi'] == 300
cases = []
for name, size, expected, custom in [('banner_A1',(96,32),(9934,3311),False),
                                     ('custom_40x60',(64,96),(4725,7087),True)]:
    source = qa / f'{name}-source.png'; dest = qa / f'{name}.png'; report = qa / f'{name}.json'
    image = Image.new('RGBA', size, (100,150,90,128)); draw = ImageDraw.Draw(image)
    draw.rectangle((3,3,size[0]//2,size[1]-4), fill=(180,70,35,255)); image.save(source)
    original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    command = [str(exe),'--self-test',str(source),'--output',str(dest),'--model','photo','--report',str(report)]
    if custom: command += ['--width-cm','40','--height-cm','60']
    # Both jobs validate the CPU fallback; GPU performance is a separate hardware test.
    command += ['--device','cpu']
    subprocess.run(command, env=env, check=True, timeout=600)
    result = json.loads(report.read_text(encoding='utf-8'))
    assert tuple(result['pixels']) == expected and result['ai_passes'] == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
    with Image.open(dest) as output:
        assert output.size == expected and output.mode == 'RGBA'
        assert output.info.get('icc_profile') and all(abs(x-300) < .01 for x in output.info['dpi'])
        assert output.getchannel('A').getextrema()[0] < 255
        assert abs(output.width*size[1]/size[0]-output.height) <= 1
        assert output.getexif().get(274,1) == 1
    cases.append({'name':name,'pixels':result['pixels'],'dpi':300,'ai_passes':1,
                  'icc_verified':True,'alpha_verified':True,'source_unchanged':True,'device':result['device']})
    # Keep reports, not large fixture outputs, in the public release artifact.
resources = Path(build['app']) / ('Contents/Resources/resources' if build['platform']=='macOS' else '_internal/resources')
manifest = json.loads((resources/'model-manifest.json').read_text(encoding='utf-8'))
for entry in manifest:
    assert hashlib.sha256((resources/entry['file']).read_bytes()).hexdigest() == entry['sha256']
summary = {'passed':True,'version':VERSION,'platform':build['platform'],'architecture':build['architecture'],
           'gui':gui,'cases':cases,'all_bundled_models_verified':True,'signing':build['signing']}
summary_path=ROOT/f'delivery/AIUpscaleKing-{VERSION}-{build["platform"]}-verification.json'
summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2), encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
