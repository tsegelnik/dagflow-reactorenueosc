from dagflow.input_extra import MissingInputAddPair
from dagflow.nodes import FunctionNode

from typing import Mapping, TYPE_CHECKING
if TYPE_CHECKING:
    from dagflow.input import Input
    from dagflow.output import Output


class EeToEnu(FunctionNode):
    """Enu(Ee, cosθ)"""
    __slots__ = (
        '_ee', '_ctheta',
        '_result',
        '_const_me', '_const_mp', '_const_mn',
        '_use_edep'
    )

    _ee: "Input"
    _ctheta: "Input"
    _result: "Output"

    _const_me: "Input"
    _const_mp: "Input"
    _const_mn: "Input"

    _use_edep: bool

    def __init__(self, name, *args, use_edep: bool=False, **kwargs):
        kwargs.setdefault("missing_input_handler", MissingInputAddPair())
        super().__init__(name, *args, **kwargs)
        self.labels.setdefaults({
                'text': r'Neutrino energy Eν, MeV',
                'plottitle': r'Neutrino energy $E_{\nu}$, MeV',
                'latex': r'$E_{\nu}$, MeV',
                'axis': r'$E_{\nu}$, MeV',
                })

        self._use_edep = use_edep

        self._ee = self._add_input(use_edep and 'edep' or 'ee', positional=True, keyword=True)
        self._ctheta = self._add_input('costheta', positional=True, keyword=True)
        self._result = self._add_output('result', positional=True, keyword=True)

        self._const_me = self._add_input('ElectronMass', positional=False, keyword=True)
        self._const_mp = self._add_input('ProtonMass', positional=False, keyword=True)
        self._const_mn = self._add_input('NeutronMass', positional=False, keyword=True)

    def _fcn(self, _, inputs, outputs):
        _enu(
            self._ee.data.ravel(),
            self._ctheta.data.ravel(),
            self._result.data.ravel(),
            self._const_me.data[0],
            self._const_mp.data[0],
            self._const_mn.data[0],
            self._use_edep
        )

    def _typefunc(self) -> None:
        """A output takes this function to determine the dtype and shape"""
        from dagflow.typefunctions import (
            check_input_dimension,
            check_inputs_equivalence,
            copy_from_input_to_output,
            assign_output_axes_from_inputs
        )

        check_input_dimension(self, slice(0, 2), 2)
        check_inputs_equivalence(self, slice(0, 2))
        eename = self._use_edep and 'edep' or 'ee'
        copy_from_input_to_output(self, eename, 'result', edges=False, meshes=False)
        assign_output_axes_from_inputs(self, (eename, 'costheta'), 'result', assign_meshes=True)

from numba import njit, void, float64, boolean
# NOTE: these functions are used only in non-numba case
from numpy.typing import NDArray
from numpy import double
from numpy import sqrt, power as pow
@njit(void(float64[:], float64[:], float64[:],
           float64, float64, float64, boolean), cache=True)
def _enu(
    EeIn: NDArray[double], CosThetaIn: NDArray[double], Result: NDArray[double],
    ElectronMass: float, ProtonMass: float, NeutronMass: float, use_edep: bool
):
    ElectronMass2 = pow(ElectronMass, 2)
    NeutronMass2 = pow(NeutronMass, 2)
    ProtonMass2 = pow(ProtonMass, 2)

    delta = 0.5*(NeutronMass2-ProtonMass2-ElectronMass2)/ProtonMass

    for i, (Ee, ctheta) in enumerate(zip(EeIn, CosThetaIn)):
        if use_edep: Ee-=ElectronMass
        if Ee>ElectronMass:
            Ve = sqrt(1.0 - ElectronMass2 / (Ee*Ee))
        else:
            Ee = ElectronMass
            Ve = 0.0
        epsilon_e = Ee / ProtonMass
        Ee0 = Ee + delta
        corr = 1.0 - epsilon_e*(1.0 - Ve*ctheta)
        Result[i] = Ee0/corr
