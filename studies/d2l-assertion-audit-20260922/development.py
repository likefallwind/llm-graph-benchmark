"""Authored, method-neutral diagnostic pairs; not independent human validation."""
from copy import deepcopy
import importlib.util
from pathlib import Path


def cases():
    spec = importlib.util.spec_from_file_location('ledger_dev_helpers', Path(__file__).with_name('evaluate.py'))
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    result = []
    def add(name, source, subject, predicate, obj, text, expected, scope='', entities=None, generic=True):
        target = dict(subject=subject, predicate=predicate, object=obj, description=text, scope=scope, polarity='positive')
        context = [{'id': 'C' + str(i + 1), 'text': s} for i, s in enumerate(source)]
        for form in ('typed', 'generic') if generic else ('typed',):
            t = deepcopy(target)
            if form == 'generic':
                t['predicate'] = 'related_to'
            result.append({'id': 'dev-' + name + '-' + form, 'expected': expected,
                'payload': {'target': t, 'segments': helper.segments(t), 'entity_context': entities or {}, 'reference_context': context}})
    src = ['流程先执行模块A，再执行模块B；模块B不会先于模块A执行。']
    add('direction-positive', src, '模块A', '先于', '模块B', '模块A先于模块B执行。', 'correct')
    add('direction-negative', src, '模块B', '先于', '模块A', '模块B先于模块A执行。', 'incorrect')
    add('field-conflict', src, '模块B', '先于', '模块A', '模块A先于模块B执行。', 'incorrect', generic=False)
    src = ['当条件H成立时，方法A保证误差降低；条件H不成立时，方法A不保证误差降低。']
    add('condition-present', src, '方法A', '降低', '误差', '条件H成立时，方法A保证误差降低。', 'correct', '条件H成立')
    add('condition-overclaim', src, '方法A', '降低', '误差', '方法A在任何条件下均保证误差降低。', 'incorrect')
    src = ['算法A用于分类。']
    add('unsupported-tail', src, '算法A', '用于', '分类', '算法A用于分类。算法A的计算速度是所有其他算法的两倍。', 'uncertain')
    add('simple-positive', src, '算法A', '用于', '分类', '算法A用于分类。', 'correct')
    add('independent-omission', ['算法A用于分类。算法A也用于聚类。'], '算法A', '用于', '分类', '算法A用于分类。', 'correct')
    src = ['图像增广又称图像增强，指通过随机翻转、裁剪等变换增加训练样本多样性，用于缓解过拟合。']
    add('synonym', src, '图像增强', '缓解', '过拟合', '图像增强用于缓解过拟合。', 'correct', entities={'subject': {'name': '图像增强', 'aliases': ['图像增广'], 'definition': '通过翻转、裁剪变换图像。'}})
    src = ['from mxnet import np\nx = np.zeros((2, 3))']
    add('import-correct', src, 'np.zeros', '属于', 'MXNet', '本代码的np.zeros属于MXNet接口。', 'correct')
    add('import-wrong', src, 'np.zeros', '属于', 'NumPy', '本代码的np.zeros属于NumPy库。', 'incorrect')
    add('import-missing', ['x = np.zeros((2, 3))'], 'np.zeros', '属于', 'NumPy', '本代码的np.zeros属于NumPy库。', 'uncertain')
    add('passive-paraphrase', ['模块B由模块A调用。'], '模块A', '调用', '模块B', '模块A调用模块B。', 'correct')
    add('compromise', ['方案A在向前和向后传播的方差约束之间取折中，不能严格同时满足两个约束。'], '方案A', '兼顾', '向前传播', '方案A兼顾向前传播的方差约束。', 'correct')
    add('contradicted-tail', ['工具A生成报告，但不提供任何文件加密功能。'], '工具A', '生成', '报告', '工具A生成报告。工具A还会加密报告文件。', 'incorrect')
    add('missing-source', [], '模型A', '包含', '模块B', '模型A包含模块B。', 'uncertain')
    add('candidate-definition-is-not-evidence', ['本节介绍模型A。'], '模型A', '包含', '模块B', '模型A包含模块B。', 'uncertain', entities={'subject': {'name': '模型A', 'aliases': [], 'definition': '模型A包含模块B。'}})
    return result
