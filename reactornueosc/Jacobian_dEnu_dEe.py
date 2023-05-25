from dagflow.input_extra import MissingInputAddPair
from dagflow.nodes import FunctionNode
from dagflow.input import Input
from dagflow.output import Output

from typing import Mapping

class Jacobian_dEnu_dEe(FunctionNode):
    """Enu(Ee, cosθ)"""
    __slots__ = (
        '_enu', '_ee', '_ctheta',
        '_result',
        '_const_me', '_const_mp', '_const_mn',
        '_use_edep'
    )

    _enu: Input
    _ee: Input
    _ctheta: Input
    _result: Output

    _const_me: Input
    _const_mp: Input
    _const_mn: Input

    _use_edep: bool

    def __init__(self, name, *args, use_edep: bool=False, **kwargs):
        kwargs.setdefault("missing_input_handler", MissingInputAddPair())
        super().__init__(name, *args, **kwargs)
        self.labels.setdefaults({
                'text': r'Energy conversion Jacobian dEν/dEdep',
                'plottitle': r'Energy conversion Jacobian $dE_{\nu}/dE_{\rm dep}$',
                'latex': r'$dE_{\nu}/dE_{\rm dep}$',
                'axis': r'$dE_{\nu}/dE_{\rm dep}$',
                })

        self._use_edep = use_edep

        self._enu = self._add_input('enu', positional=True, keyword=True)
        self._ee = self._add_input(use_edep and 'edep' or 'ee', positional=True, keyword=True)
        self._ctheta = self._add_input('costheta', positional=True, keyword=True)
        self._result = self._add_output('result', positional=True, keyword=True)

        self._const_me   = self._add_input('ElectronMass', positional=False, keyword=True)
        self._const_mp   = self._add_input('ProtonMass', positional=False, keyword=True)

    def _fcn(self, _, inputs, outputs):
        _jacobian_dEnu_dEe(
            self._enu.data.ravel(),
            self._ee.data.ravel(),
            self._ctheta.data.ravel(),
            self._result.data.ravel(),
            self._const_me.data[0],
            self._const_mp.data[0],
            self._use_edep
        )

    def _typefunc(self) -> None:
        """A output takes this function to determine the dtype and shape"""
        from dagflow.typefunctions import (
            assign_output_axes_from_inputs,
            check_input_dimension,
            check_inputs_equivalence,
            copy_from_input_to_output
        )
        check_input_dimension(self, slice(0, 3), 2)
        check_inputs_equivalence(self, slice(0, 3))
        eename = self._use_edep and 'edep' or 'ee'
        copy_from_input_to_output(self, eename, 'result', edges=False, nodes=False)
        assign_output_axes_from_inputs(self, (eename, 'costheta'), 'result', assign_nodes=True)


from numba import njit, void, float64, boolean
# NOTE: these functions are used only in non-numba case
from numpy.typing import NDArray
from numpy import double
from numpy import sqrt, power as pow
@njit(void(float64[:], float64[:], float64[:], float64[:],
           float64, float64, boolean), cache=True)
def _jacobian_dEnu_dEe(
    EnuIn: NDArray[double],
    EeIn: NDArray[double],
    CosThetaIn: NDArray[double],
    Result: NDArray[double],
    ElectronMass: float,
    ProtonMass: float,
    use_edep: bool
):
    ElectronMass2 = pow(ElectronMass, 2)

    for i, (Enu, Ee, ctheta) in enumerate(zip(EnuIn, EeIn, CosThetaIn)):
        if use_edep: Ee-=ElectronMass
        if Ee<=ElectronMass:
            Result[i] = 0.0
            continue
        Ve = sqrt(1.0 - ElectronMass2 / (Ee*Ee))
        nominator = ProtonMass + Enu*(1.0-ctheta/Ve)
        denominator = ProtonMass - Ee*(1-Ve*ctheta)
        if denominator<=0:
            Result[i] = 0.0
            continue
        Result[i] = nominator/denominator
