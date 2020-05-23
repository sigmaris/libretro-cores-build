def main(ctx):
    return [
        pipeline("bullseye", "misc", "2048,3dengine"),
        pipeline("bullseye", "beetle", "beetle*"),
#        pipeline("bullseye", "mame", "mame"),
        pipeline("bullseye", "fba", "fbalpha2012*"),
        pipeline("bullseye", "nintendo", "bsnes,citra,desmume,dolphin,fceumm,gambatte,gw,melonDS,meteor,nestopia,parallel-n64,PokeMini,QuickNES_Core,SameBoy,snes9x,snes9x2005,snes9x2010,vba-next,vbam"),
    ]


def pipeline(suite, name, pattern):
    return {
        "kind": "pipeline",
        "type": "docker",
        "name": "build_%s" % name,
        "platform": {
            "os": "linux",
            "arch": "arm64",
        },
        "workspace": {
            "base": "/drone",
            "path": "src",
        },
        "trigger": {
            "ref": [
                "refs/heads/master",
                "refs/tags/*",
            ]
        },
        "steps": [
            {
                "name": "build",
                "image": "sigmaris/libretrobuilder:%s" % suite,
                "commands": [
                    "mkdir /drone/build",
                    "cd /drone/build",
                    "python3 /drone/src/core_builder.py --include '%s' %s" % (pattern, suite),
                ],
            },
        ],
    }
