from pip.req import parse_requirements

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
    
# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements("requirements.txt")
# reqs is a list of requirement
reqs = [str(ir.req) for ir in install_reqs]

setup(name="wot",
      description="generating context-free grammars of content",
      author="Resilient Science, Inc.",
      author_email="info@resilientscience.com",
      url="http://resilientscience.github.io/wot/",
      version="0.1",
      scripts=[],
      packages=["wot", "wot.sequitur", "wot.mapreduce"],
      license="BSD",
      install_requires=reqs,)
