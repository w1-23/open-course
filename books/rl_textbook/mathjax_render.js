// Render every LaTeX fragment in the corpus to an SVG via MathJax 3.
// Invoked by mathjax.py:  node mathjax_render.js <input.json> <output.json>
//
// IMPORTANT: MathJax registers a TeX package ONLY as a side effect of requiring
// its `*Configuration.js` module.  Passing a package name in
// `new TeX({packages: [...]})` is silently ignored when the module was never
// loaded (ParserConfiguration.addPackage does `conf && add(...)`), and the
// symptom is a silent `<g data-mml-node="merror">` SVG whose background <rect>
// paints a solid black bar.  AllPackages.js cannot be required wholesale here
// because it pulls in mhchem, whose peer dependency is not vendored, so the
// modules are required one by one below.

const fs = require('fs');
const path = require('path');

const MJ = path.join(__dirname, 'vendor', 'mathjax');
const { mathjax } = require(path.join(MJ, 'js', 'mathjax.js'));
const { TeX } = require(path.join(MJ, 'js', 'input', 'tex.js'));
const { SVG } = require(path.join(MJ, 'js', 'output', 'svg.js'));
const { liteAdaptor } = require(path.join(MJ, 'js', 'adaptors', 'liteAdaptor.js'));
const { RegisterHTMLHandler } = require(path.join(MJ, 'js', 'handlers', 'html.js'));

const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);

// name -> relative Configuration module, mirroring js/input/tex/AllPackages.js
// minus mhchem (its `mhchemparser` dependency is not vendored).
const CONFIG_MODULES = {
  base: 'base/BaseConfiguration.js',
  action: 'action/ActionConfiguration.js',
  ams: 'ams/AmsConfiguration.js',
  amscd: 'amscd/AmsCdConfiguration.js',
  bbox: 'bbox/BboxConfiguration.js',
  boldsymbol: 'boldsymbol/BoldsymbolConfiguration.js',
  braket: 'braket/BraketConfiguration.js',
  bussproofs: 'bussproofs/BussproofsConfiguration.js',
  cancel: 'cancel/CancelConfiguration.js',
  cases: 'cases/CasesConfiguration.js',
  centernot: 'centernot/CenternotConfiguration.js',
  color: 'color/ColorConfiguration.js',
  colorv2: 'colorv2/ColorV2Configuration.js',
  colortbl: 'colortbl/ColortblConfiguration.js',
  configmacros: 'configmacros/ConfigMacrosConfiguration.js',
  empheq: 'empheq/EmpheqConfiguration.js',
  enclose: 'enclose/EncloseConfiguration.js',
  extpfeil: 'extpfeil/ExtpfeilConfiguration.js',
  gensymb: 'gensymb/GensymbConfiguration.js',
  html: 'html/HtmlConfiguration.js',
  mathtools: 'mathtools/MathtoolsConfiguration.js',
  newcommand: 'newcommand/NewcommandConfiguration.js',
  noerrors: 'noerrors/NoErrorsConfiguration.js',
  noundefined: 'noundefined/NoUndefinedConfiguration.js',
  physics: 'physics/PhysicsConfiguration.js',
  setoptions: 'setoptions/SetOptionsConfiguration.js',
  tagformat: 'tagformat/TagFormatConfiguration.js',
  textcomp: 'textcomp/TextcompConfiguration.js',
  textmacros: 'textmacros/TextMacrosConfiguration.js',
  upgreek: 'upgreek/UpgreekConfiguration.js',
  unicode: 'unicode/UnicodeConfiguration.js',
  verb: 'verb/VerbConfiguration.js',
};

// Packages that may safely fail (e.g. they need a missing peer dependency) as
// long as the core set below still loads.
const CORE = ['base', 'ams', 'newcommand', 'autoload', 'require', 'noundefined'];

const loaded = [];
const skipped = [];
for (const [name, rel] of Object.entries(CONFIG_MODULES)) {
  try {
    require(path.join(MJ, 'js', 'input', 'tex', rel));
    loaded.push(name);
  } catch (err) {
    skipped.push(name + ': ' + String(err && err.message || err));
  }
}
const missingCore = CORE.filter((c) => !loaded.includes(c) && c !== 'autoload' && c !== 'require');
if (missingCore.length) {
  console.error('FATAL: core MathJax packages failed to load: ' + missingCore.join(', '));
  console.error(skipped.join('\n'));
  process.exit(2);
}

// 'autoload' and 'require' are base packages with no standalone Configuration
// module; TeX loads them from the base bundle.
const PACKAGES = loaded.concat(['autoload', 'require']);

const tex = new TeX({ packages: PACKAGES });
const svg = new SVG({ fontCache: 'local' });
const doc = mathjax.document('', { InputJax: tex, OutputJax: svg });

const [, , inPath, outPath] = process.argv;

// --- self test: these must render, otherwise we are about to emit black bars.
function selfTest() {
  const probes = [
    ['\\operatorname{decode}(x)', false],
    ['\\begin{bmatrix}1&2\\\\3&4\\end{bmatrix}', true],
    ['\\mathbb{R}^{n}', false],
    ['\\le', false],
    ['\\xleftrightarrow{abc}', false],
  ];
  const bad = [];
  for (const [src, display] of probes) {
    let out = '';
    try {
      out = adaptor.innerHTML(doc.convert(src, { display }));
    } catch (err) {
      bad.push(src + ' -> ' + String(err && err.message || err));
      continue;
    }
    if (/data-mjx-error|data-mml-node="merror"/.test(out)) {
      const m = out.match(/data-mjx-error="([^"]*)"/);
      bad.push(src + ' -> merror: ' + (m ? m[1] : 'unknown'));
    }
  }
  return bad;
}

const selfTestProblems = selfTest();
// One transient failure is tolerated; two or more means the package wiring is
// broken and every formula in the corpus would silently become a black bar.
if (selfTestProblems.length >= 2) {
  console.error('FATAL: MathJax package wiring is broken.');
  for (const p of selfTestProblems) console.error('  ' + p);
  console.error('loaded: ' + loaded.join(', '));
  console.error('skipped:\n' + skipped.join('\n'));
  process.exit(3);
}

const payload = JSON.parse(fs.readFileSync(inPath, 'utf8').replace(/^\uFEFF/, ''));

const t0 = Date.now();
const results = [];
const failures = [];
const cache = new Map();

for (const item of payload.items) {
  const key = item.key;
  if (cache.has(key)) {
    results.push({ key, ok: true, svg: cache.get(key) });
    continue;
  }
  try {
    const node = doc.convert(item.src, { display: !!item.display });
    const out = adaptor.innerHTML(node);
    const m = out.match(/<svg[\s\S]*<\/svg>/);
    if (!m) throw new Error('no <svg> in output');

    // A MathJax parse error does not throw: it emits an merror tree whose
    // background rect paints a solid black bar.  Treat it as a hard failure.
    const errMatch = out.match(/data-mjx-error="([^"]*)"/);
    if (errMatch || /data-mml-node="merror"/.test(out)) {
      throw new Error('merror: ' + (errMatch ? errMatch[1] : 'unknown'));
    }

    // MathJax's default TeX glyphs are visually heavier than the Chinese body
    // face and Times New Roman used for Latin prose.  Reduce the overall ink
    // density so equations sit more naturally beside the surrounding text.
    const renderedSvg = m[0].replace(/^<svg\b/, '<svg opacity="0.78"');
    cache.set(key, renderedSvg);
    results.push({ key, ok: true, svg: renderedSvg });
  } catch (err) {
    const msg = String(err && err.message || err);
    failures.push({ key, src: item.src, error: msg });
    results.push({ key, ok: false, error: msg });
  }
}

fs.writeFileSync(outPath, JSON.stringify({
  ok: results.filter((r) => r.ok).length,
  total: results.length,
  ms: Date.now() - t0,
  packages: PACKAGES,
  skipped,
  selfTest: selfTestProblems,
  failures,
  results,
}, null, 0), 'utf8');

console.log(`rendered ${results.filter((r) => r.ok).length}/${results.length} in ${Date.now() - t0}ms, failures=${failures.length}, packages=${PACKAGES.length}`);
