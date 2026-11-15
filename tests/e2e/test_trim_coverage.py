"""Dense subpixel triangles and fast strokes must not leave trim speckles."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


SETUP = """async () => {
  const THREE = await import('/vendor/three.module.js');
  const {createScreenTrimBrush} = await import('/screen_trim_brush.js');
  const host = document.createElement('div');
  host.style='position:fixed;left:0;top:0;width:400px;height:300px'; document.body.append(host);
  const renderer = new THREE.WebGLRenderer(); renderer.setSize(400,300); host.append(renderer.domElement);
  const camera = new THREE.PerspectiveCamera(36,4/3,.1,2000);
  camera.position.set(0,0,100); camera.lookAt(0,0,0); camera.updateMatrixWorld();
  window.trimHarness = {THREE,host,renderer,camera,createScreenTrimBrush};
}"""


@pytest.mark.parametrize("slope", [0, 0.8])
def test_dense_surface_selected_once_without_hidden_surface_removal(server_url, slope):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url + "/region-review.html")
            page.evaluate(SETUP)
            result = page.evaluate("""async slope => {
              const {THREE,host,renderer,camera,createScreenTrimBrush}=trimHarness;
              const vertices=[], n=48;
              for(const z of [0,-.02,-3]) for(let x=0;x<n;x++) for(let y=0;y<n;y++) {
                const a=x/n-.5,b=y/n-.5,d=1/n;
                vertices.push(a,b,z,a+d,b,z,a,b+d,z,a+d,b,z,a+d,b+d,z,a,b+d,z);
              }
              for(let i=0;i<vertices.length;i+=3) vertices[i+2]+=slope*vertices[i];
              const count=2*n*n, geometry=new THREE.BufferGeometry();
              geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
              const brush=createScreenTrimBrush(renderer,host,camera,geometry,()=>new THREE.Vector3());
              brush.show({mode:'trim',radius:2},{clientX:200,clientY:150});
              const started=performance.now(), selected=brush.select();
              const duration=performance.now()-started;
              const {binaryStl,meshHash}=await import('/surface_repair_mesh.js');
              const {trimSurface}=await import('/surface_trim.js');
              const bytes=binaryStl(new Float32Array(vertices)),labels=new Uint8Array(count*3);
              labels[0]=31; labels[count*2]=41;
              const scan={bytes,sha256:await meshHash(bytes),filename:'dense.stl',arch:'lower',rotation:[1,1,1]};
              const next=await trimSurface(scan,labels,selected,true);
              brush.dispose();geometry.dispose();renderer.dispose();host.remove();
              return {count,front:selected.filter(f=>f<count).length,roughness:selected.filter(f=>f>=count&&f<count*2).length,
                back:selected.filter(f=>f>=count*2).length,
                retained:next.labels.length,painted:next.labels[0],duration};
            }""", slope)
            assert result["front"] == result["count"], result
            assert result["roughness"] == result["count"], result
            assert result["back"] == 0, result
            assert result["retained"] == result["count"], result
            assert result["painted"] == 41
        finally:
            browser.close()


def test_fast_stroke_fills_gaps_but_separate_clicks_do_not_connect(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url + "/region-review.html")
            page.evaluate(SETUP)
            result = page.evaluate("""() => {
              const {THREE,host,renderer,camera,createScreenTrimBrush}=trimHarness;
              const vertices=[];
              for(const x of [-8,0,8]) vertices.push(x-.3,-.3,0,x+.3,-.3,0,x,.3,0);
              const geometry=new THREE.BufferGeometry();
              geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));
              const brush=createScreenTrimBrush(renderer,host,camera,geometry,()=>new THREE.Vector3());
              const paint=x=>{
                const p=new THREE.Vector3(x,0,0).project(camera);
                brush.show({mode:'trim',radius:.2},{clientX:(p.x+1)*200,clientY:150});
                return brush.select();
              };
              const first=paint(-8),swept=paint(8);brush.endStroke();
              const separate=paint(-8);
              brush.dispose();geometry.dispose();renderer.dispose();host.remove();
              return {first,swept,separate};
            }""")
            assert result["first"] == [0]
            assert sorted(result["swept"]) == [0, 1, 2]
            assert result["separate"] == [0]
        finally:
            browser.close()


def test_real_h6_trim_preview_apply_and_undo(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "paintings"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/region-review.html?baseline=lower&visit=progress-02&capture=fusion-h-6")
            expect(page.locator("#reviewSource")).to_contain_text("587,840 faces", timeout=60000)
            page.locator("#trimPanel summary").click()
            page.locator("#reviewRadius").fill("3")
            page.locator('[data-review-mode="trim"]').click()
            canvas = page.locator("#regionCanvas canvas")
            box = canvas.bounding_box()
            canvas.screenshot(path=str(tmp_path / "h6-before.png"))
            for x, y in [(.7, .55), (.7, .7), (.5, .75), (.3, .6)]:
                canvas.click(position={"x": box["width"] * x, "y": box["height"] * y})
            expect(page.locator("#trimApply")).to_be_enabled()
            expect(page.locator("#trimAllowPainted")).to_have_count(0)
            canvas.screenshot(path=str(tmp_path / "h6-red-selection.png"))
            page.locator("#trimApply").click()
            expect(page.locator("#reviewSource")).to_contain_text("Trimmed surface copy")
            expect(page.locator("#reviewSource")).not_to_contain_text("587,840 faces")
            canvas.screenshot(path=str(tmp_path / "h6-after.png"))
            page.locator("#repairUndo").click()
            expect(page.locator("#reviewSource")).to_contain_text("587,840 faces")
            assert not errors
        finally:
            browser.close()
