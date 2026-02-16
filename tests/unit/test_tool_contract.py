import pytest
from framework.data import DataContract
from framework.engine.native_engine import NativeEngine
from framework.types import PlanStep
from framework.actor.base_actor import Actor
from framework.tools.contracts import tool_contract

# --- Example DataContracts ---


# --- Example DataContracts ---
class EmployeeData(DataContract):
    employee_id: str
    name: str
    department: str


class EquipmentOrder(DataContract):
    order_id: str
    model: str
    delivery_date: str


# --- Example Actor and Tool ---
class ProvisioningActor(Actor):
    def configure(self):
        self.name = "ProvisioningActor"
        self.tools = [self.create_order]

    @tool_contract(input=EmployeeData, output=EquipmentOrder)
    def create_order(self, data: EmployeeData) -> EquipmentOrder:
        return EquipmentOrder(
            order_id="ORD-123", model="MacBook Pro", delivery_date="2024-01-15"
        )


# --- Untyped Tool for Backward Compatibility ---
class UntypedActor(Actor):
    def configure(self):
        self.name = "UntypedActor"
        self.tools = [self.untyped_tool]

    def untyped_tool(self, data):
        return {"result": "ok"}


@pytest.mark.asyncio
async def test_tool_contract_metadata():
    actor = ProvisioningActor()
    contract = actor.create_order.__tool_contract__
    assert contract.input is EmployeeData
    assert contract.output is EquipmentOrder


@pytest.mark.asyncio
async def test_input_validation():
    actor = ProvisioningActor()
    actor.configure()
    engine = NativeEngine()
    step = PlanStep(
        actor_name=actor.name,
        tool_name="create_order",
        parameters={"data": {"employee_id": "1", "name": "John"}},  # missing department
        status="pending",
    )
    from framework.actor.registry import ActorRegistry

    ActorRegistry.register(actor.name, actor.__class__)

    result = await engine.execute_step(step, {})
    assert result.status == "error"
    assert "department" in (result.error or "")


@pytest.mark.asyncio
async def test_output_validation(monkeypatch):
    class PatchedProvisioningActor(ProvisioningActor):
        def __init__(self):
            # Do not call super().__init__ to avoid setting self.tools
            self.name = "ProvisioningActor"

        def configure(self):
            # Override to avoid assigning self.tools
            self.name = "ProvisioningActor"

        @property
        def tools(self):
            return [self.create_order]

    actor = PatchedProvisioningActor()
    engine = NativeEngine()

    def bad_output(self, data):
        return {"order_id": "ORD-123", "model": "MacBook Pro"}  # missing delivery_date

    bad_output.__name__ = "create_order"
    patched_method = tool_contract(input=EmployeeData, output=EquipmentOrder)(
        bad_output
    )
    monkeypatch.setattr(PatchedProvisioningActor, "create_order", patched_method)
    # Also set on the instance to ensure the engine finds it
    bound_method = patched_method.__get__(actor)
    setattr(actor, "create_order", bound_method)
    from framework.actor.registry import ActorRegistry

    # Patch ActorRegistry.get to always return our patched actor instance
    monkeypatch.setattr(ActorRegistry, "get", lambda name, **kwargs: actor)

    step = PlanStep(
        actor_name=actor.name,
        tool_name="create_order",
        parameters={"data": {"employee_id": "1", "name": "John", "department": "IT"}},
        status="pending",
    )

    result = await engine.execute_step(step, {})
    assert result.status == "error"
    assert "delivery_date" in (result.error or "")


@pytest.mark.asyncio
async def test_backward_compatibility():
    actor = UntypedActor()
    actor.configure()
    engine = NativeEngine()
    step = PlanStep(
        actor_name=actor.name,
        tool_name="untyped_tool",
        parameters={"data": {"foo": "bar"}},
        status="pending",
    )
    from framework.actor.registry import ActorRegistry

    ActorRegistry.register(actor.name, actor.__class__)

    result = await engine.execute_step(step, {})
    # If the tool fails, result.status will be 'error' and output may be empty
    if result.status == "success":
        assert result.output["result"] == "ok"
    else:
        assert False, f"Untyped tool failed: {result.error}"


@pytest.mark.asyncio
async def test_tool_contract_attribute_access():
    actor = ProvisioningActor()
    contract = actor.create_order.__tool_contract__
    assert hasattr(actor.create_order, "__tool_contract__")
    assert contract.input is EmployeeData
    assert contract.output is EquipmentOrder
