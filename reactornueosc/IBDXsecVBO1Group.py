from typing import TYPE_CHECKING

from dagflow.metanode import MetaNode

from .EeToEnu import EeToEnu
from .IBDXsecVBO1 import IBDXsecVBO1
from .Jacobian_dEnu_dEe import Jacobian_dEnu_dEe

if TYPE_CHECKING:
    from dagflow.lib.IntegratorGroup import IntegratorGroup
    from dagflow.storage import NodeStorage

class IBDXsecVBO1Group(MetaNode):
    __slots__ = ('_eename', )
    _eename: str

    def __init__(
        self,
        name_ibd: str = 'ibd',
        name_enu: str = 'enu',
        name_jacobian: str = 'jacobian',
        *,
        use_edep: bool=False,
        labels: dict={}
    ):
        super().__init__(strategy="Disable")

        ibdxsec = IBDXsecVBO1(name_ibd, label=labels.get('xsec', {}))
        eetoenu = EeToEnu(name_enu, use_edep=use_edep, label=labels.get('enu', {}))
        jacobian = Jacobian_dEnu_dEe(name_jacobian, use_edep=use_edep, label=labels.get('jacobian', {}))

        eetoenu.outputs['result'] >> (jacobian.inputs['enu'], ibdxsec.inputs['enu'])

        self._eename = use_edep and 'edep' or 'ee'
        inputs_common = ['ElectronMass', 'ProtonMass', 'NeutronMass']
        inputs_ibd = inputs_common+[ 'NeutronLifeTime', 'PhaseSpaceFactor', 'g', 'f', 'f2' ]
        merge_inputs = [self._eename, 'costheta']+inputs_common
        self._add_node(
            ibdxsec,
            kw_inputs=['costheta']+inputs_ibd,
            merge_inputs=merge_inputs,
            outputs_pos=True
        )
        self._add_node(
            eetoenu,
            kw_inputs=[self._eename, 'costheta']+inputs_common,
            merge_inputs=merge_inputs,
            kw_outputs={'result': 'enu'}
        )
        self._add_node(
            jacobian,
            kw_inputs=['enu', self._eename, 'costheta']+inputs_common[:-1],
            merge_inputs=merge_inputs[:-1],
            kw_outputs={'result': 'jacobian'}
        )
        self.inputs.make_positionals(self._eename, 'costheta')

    @classmethod
    def make_stored(
        cls,
        name_ibd: str = 'ibd.crosssection',
        name_enu: str = 'ibd.enu',
        name_jacobian: str = 'ibd.jacobian',
        *args,
        **kwargs
    ) -> tuple["IntegratorGroup", "NodeStorage"]:
        from dagflow.storage import NodeStorage
        storage = NodeStorage(default_containers=True)
        nodes = storage.child('nodes')
        inputs = storage.child('inputs')
        outputs = storage.child('outputs')

        ibd = cls(name_ibd, name_enu, name_jacobian, *args, **kwargs)

        nodes[name_ibd] = ibd
        inputs[name_ibd, ibd._eename] = ibd.inputs[ibd._eename]
        inputs[name_ibd, 'costheta'] = ibd.inputs['costheta']
        outputs[name_ibd] = ibd.outputs['result']
        outputs[name_enu] = ibd.outputs['enu']
        outputs[name_jacobian] = ibd.outputs['jacobian']

        NodeStorage.update_current(storage, strict=True)

        return ibd, storage
