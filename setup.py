from setuptools import setup, find_packages

setup(
    name='recitation-bot',
    version='0.1',
    description='Mediawiki bot to upload academic journal articles.',
    url='https://github.com/wpoa/recitation-bot',
    author='WikiProject Open Access',
    license='GPLv3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 2.7',
    ],
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=['beautifulsoup4', 'httplib2', 'requests', 'wget']
)
