"""
Seed katalog badge awal: 8 kategori x 3 level = 24 badge.

Idempotent: jalankan ulang aman, akan `update_or_create` berdasarkan `code`.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.badges.models import Badge, BadgeCategory, BadgeLevel


LEVEL_KEYWORDS = {
    BadgeLevel.PEMULA: [
        'beginner', 'pemula', 'basic', 'intro', 'introductory', 'fundamental', 'fundamentals',
        'dasar', 'foundation', 'foundational', 'starter', 'all levels', 'all level', 'any level',
        'general',
    ],
    BadgeLevel.MENENGAH: ['intermediate', 'menengah', 'medium', 'mid'],
    BadgeLevel.MAHIR: ['advanced', 'mahir', 'expert', 'mastery', 'lanjutan'],
}


LEVEL_LABEL = {
    BadgeLevel.PEMULA: 'Pemula',
    BadgeLevel.MENENGAH: 'Menengah',
    BadgeLevel.MAHIR: 'Mahir',
}


CATEGORY_DEFS = [
    {
        'category': BadgeCategory.UI_UX,
        'display': 'UI/UX',
        'slug_root': 'ui-ux',
        'tags_any': [
            'ui', 'ux', 'ui/ux', 'ui-ux', 'ui ux', 'ui design', 'ux design',
            'user experience', 'user interface', 'figma', 'adobe xd', 'sketch',
            'wireframe', 'wireframing', 'prototyping', 'design system',
            'interaction design', 'usability', 'visual design',
        ],
    },
    {
        'category': BadgeCategory.FRONTEND,
        'display': 'Frontend',
        'slug_root': 'frontend',
        'tags_any': [
            'frontend', 'front-end', 'front end', 'html', 'css', 'javascript', 'typescript',
            'react', 'react js', 'react.js', 'vue', 'vue.js', 'angular', 'next.js', 'nextjs',
            'svelte', 'tailwind', 'tailwindcss', 'bootstrap', 'sass', 'jquery',
            'web design',
        ],
    },
    {
        'category': BadgeCategory.BACKEND,
        'display': 'Backend',
        'slug_root': 'backend',
        'tags_any': [
            'backend', 'back-end', 'back end', 'node', 'node.js', 'nodejs', 'express',
            'django', 'flask', 'fastapi', 'spring', 'spring boot', 'laravel',
            'ruby on rails', 'rails', 'rest api', 'restful', 'graphql', 'php',
            'golang', 'rust', 'java', 'c#', '.net', 'asp.net', 'server side',
            'microservices',
        ],
    },
    {
        'category': BadgeCategory.MOBILE,
        'display': 'Mobile',
        'slug_root': 'mobile',
        'tags_any': [
            'android', 'ios', 'kotlin', 'swift', 'react native', 'flutter',
            'jetpack compose', 'swiftui', 'mobile app', 'mobile apps',
            'mobile programming', 'android development', 'ios development',
            'objective-c', 'dart',
        ],
    },
    {
        'category': BadgeCategory.DATA_SCIENCE,
        'display': 'Data Science',
        'slug_root': 'data-science',
        'tags_any': [
            'data science', 'data analysis', 'data analytics', 'data analyst',
            'pandas', 'numpy', 'data visualization', 'tableau', 'power bi',
            'sql', 'statistics', 'excel', 'bigquery', 'data engineering', 'etl',
            'data-driven decision-making', 'business analytics',
        ],
    },
    {
        'category': BadgeCategory.ML_AI,
        'display': 'Machine Learning',
        'slug_root': 'ml-ai',
        'tags_any': [
            'machine learning', 'deep learning', 'ai', 'artificial intelligence',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn',
            'neural network', 'neural networks', 'nlp', 'natural language processing',
            'computer vision', 'llm', 'large language modeling', 'large language models',
            'generative ai', 'transformers', 'mlops', 'reinforcement learning',
            'supervised learning', 'unsupervised learning',
        ],
    },
    {
        'category': BadgeCategory.DEVOPS,
        'display': 'DevOps',
        'slug_root': 'devops',
        'tags_any': [
            'devops', 'docker', 'kubernetes', 'k8s', 'ci/cd', 'cicd', 'jenkins',
            'github actions', 'gitlab ci', 'terraform', 'ansible', 'aws', 'azure',
            'gcp', 'google cloud', 'google cloud platform', 'cloud computing',
            'linux', 'infrastructure', 'sre', 'site reliability', 'monitoring',
            'observability',
        ],
    },
    {
        'category': BadgeCategory.CYBERSECURITY,
        'display': 'Cybersecurity',
        'slug_root': 'cybersecurity',
        'tags_any': [
            'cybersecurity', 'cyber security', 'ethical hacking', 'penetration testing',
            'pentest', 'pen test', 'network security', 'cryptography', 'malware',
            'forensics', 'digital forensics', 'siem', 'soc analyst', 'owasp',
            'web security', 'information security', 'infosec',
        ],
    },
]


LEVEL_DESCRIPTIONS = {
    BadgeLevel.PEMULA: 'Selesaikan course {display} pertamamu di level pemula.',
    BadgeLevel.MENENGAH: 'Selesaikan course {display} di level menengah.',
    BadgeLevel.MAHIR: 'Selesaikan course {display} di level mahir.',
}


def build_badge_payloads():
    payloads = []
    sort_order = 0
    for cat_def in CATEGORY_DEFS:
        for level in [BadgeLevel.PEMULA, BadgeLevel.MENENGAH, BadgeLevel.MAHIR]:
            sort_order += 1
            code = f"{cat_def['slug_root']}-{level.value}"
            name = f"{cat_def['display']} {LEVEL_LABEL[level]}"
            payloads.append({
                'code': code,
                'name': name,
                'description': LEVEL_DESCRIPTIONS[level].format(display=cat_def['display']),
                'category': cat_def['category'].value,
                'level': level.value,
                'criteria': {
                    'tags_any': cat_def['tags_any'],
                    'level_any': LEVEL_KEYWORDS[level],
                },
                'sort_order': sort_order,
            })
    return payloads


class Command(BaseCommand):
    help = 'Seed katalog badge awal (8 kategori x 3 level = 24 badge). Idempotent.'

    def handle(self, *args, **options):
        payloads = build_badge_payloads()
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for payload in payloads:
                code = payload['code']
                defaults = {k: v for k, v in payload.items() if k != 'code'}
                defaults['is_active'] = True
                _, created = Badge.objects.update_or_create(code=code, defaults=defaults)
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seed selesai. Created: {created_count}, Updated: {updated_count}, '
            f'Total catalog: {Badge.objects.count()}'
        ))
