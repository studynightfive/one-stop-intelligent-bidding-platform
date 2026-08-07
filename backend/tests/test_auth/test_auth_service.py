"""Auth 模块测试.

测试 User 模型、AuthService、UserService 等。
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import InvalidCredentialsError, ValidationError
from app.domains.auth.models.user import User, UserRole, UserStatus
from app.domains.auth.services.auth_service import AuthService
from app.domains.auth.services.user_service import UserService
from app.core.security import get_password_hash, verify_password


class TestUserModel:
    """User 模型测试."""

    def test_user_role_enum_values(self) -> None:
        """测试 UserRole 枚举值."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PROJECT_LEAD.value == "project_lead"
        assert UserRole.MEMBER.value == "member"
        assert UserRole.REVIEWER.value == "reviewer"

    def test_user_status_enum_values(self) -> None:
        """测试 UserStatus 枚举值."""
        assert UserStatus.INVITED.value == "invited"
        assert UserStatus.ACTIVE.value == "active"
        assert UserStatus.DISABLED.value == "disabled"

    def test_user_is_active_property(self) -> None:
        """测试 is_active 属性."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            name="Test",
            role=UserRole.MEMBER,
            status=UserStatus.INVITED,
        )
        assert not user.is_active

        user.status = UserStatus.ACTIVE
        assert user.is_active

        user.status = UserStatus.DISABLED
        assert not user.is_active

    def test_user_can_manage_users_property(self) -> None:
        """测试 can_manage_users 属性."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            name="Test",
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
        )
        assert not user.can_manage_users

        user.role = UserRole.ADMIN
        assert user.can_manage_users

    def test_user_can_create_projects_property(self) -> None:
        """测试 can_create_projects 属性."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            name="Test",
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
        )
        assert not user.can_create_projects

        user.role = UserRole.PROJECT_LEAD
        assert user.can_create_projects

        user.role = UserRole.ADMIN
        assert user.can_create_projects

    def test_user_can_review_property(self) -> None:
        """测试 can_review 属性."""
        user = User(
            id=uuid4(),
            tenant_id=uuid4(),
            email="test@example.com",
            name="Test",
            role=UserRole.MEMBER,
            status=UserStatus.ACTIVE,
        )
        assert not user.can_review

        user.role = UserRole.REVIEWER
        assert user.can_review

        user.role = UserRole.PROJECT_LEAD
        assert user.can_review

        user.role = UserRole.ADMIN
        assert user.can_review

    def test_user_to_dict(self) -> None:
        """测试 to_dict 方法."""
        user_id = uuid4()
        tenant_id = uuid4()

        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email="test@example.com",
            name="Test User",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
        )

        result = user.to_dict()

        assert result["id"] == str(user_id)
        assert result["tenant_id"] == str(tenant_id)
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        assert result["role"] == "admin"
        assert result["status"] == "active"
        # password_hash 不应出现在 to_dict 中
        assert "password_hash" not in result


class TestPasswordHashing:
    """密码哈希测试."""

    def test_password_hash_and_verify(self) -> None:
        """测试密码哈希和验证."""
        password = "SecurePassword123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self) -> None:
        """测试错误密码验证失败."""
        password = "SecurePassword123"
        hashed = get_password_hash(password)

        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes_for_same_password(self) -> None:
        """测试同一密码生成不同哈希（salt）."""
        password = "SecurePassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # bcrypt 应该为同一密码生成不同的哈希
        assert hash1 != hash2
        # 但两者都应该能验证通过
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestAuthService:
    """AuthService 测试."""

    @pytest_asyncio.fixture
    async def auth_service(self, db_session: AsyncSession) -> AuthService:
        """创建 AuthService 实例."""
        return AuthService(db_session)

    @pytest.mark.asyncio
    async def test_register_user(self, auth_service: AuthService) -> None:
        """测试用户注册."""
        tenant_id = uuid4()

        user = await auth_service.register(
            email="newuser@example.com",
            password="Password123",
            name="New User",
            tenant_id=tenant_id,
        )

        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.name == "New User"
        assert user.tenant_id == tenant_id
        assert user.status == UserStatus.ACTIVE
        assert user.password_hash is not None
        assert verify_password("Password123", user.password_hash)

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, auth_service: AuthService) -> None:
        """测试重复邮箱注册失败."""
        tenant_id = uuid4()

        # 第一次注册
        await auth_service.register(
            email="duplicate@example.com",
            password="Password123",
            name="User 1",
            tenant_id=tenant_id,
        )

        # 第二次注册同一邮箱
        with pytest.raises(ValidationError):
            await auth_service.register(
                email="duplicate@example.com",
                password="Password456",
                name="User 2",
                tenant_id=tenant_id,
            )

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_service: AuthService) -> None:
        """测试认证成功."""
        tenant_id = uuid4()

        # 注册用户
        user = await auth_service.register(
            email="auth@example.com",
            password="TestPassword123",
            name="Auth Test",
            tenant_id=tenant_id,
        )

        # 认证
        authenticated = await auth_service.authenticate(
            email="auth@example.com",
            password="TestPassword123",
        )

        assert authenticated.id == user.id
        assert authenticated.email == user.email

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_service: AuthService) -> None:
        """测试密码错误认证失败."""
        tenant_id = uuid4()

        # 注册用户
        await auth_service.register(
            email="wrongpass@example.com",
            password="CorrectPassword123",
            name="Test User",
            tenant_id=tenant_id,
        )

        # 使用错误密码认证
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate(
                email="wrongpass@example.com",
                password="WrongPassword",
            )

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self, auth_service: AuthService) -> None:
        """测试用户不存在认证失败."""
        with pytest.raises(InvalidCredentialsError):
            await auth_service.authenticate(
                email="nonexistent@example.com",
                password="Password123",
            )

    @pytest.mark.asyncio
    async def test_create_tokens(self, auth_service: AuthService) -> None:
        """测试创建 Token."""
        tenant_id = uuid4()

        user = await auth_service.register(
            email="token@example.com",
            password="Password123",
            name="Token Test",
            tenant_id=tenant_id,
        )

        tokens = await auth_service.create_tokens(user)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "Bearer"
        assert "expires_in" in tokens
        assert len(tokens["access_token"]) > 0
        assert len(tokens["refresh_token"]) > 0

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, auth_service: AuthService) -> None:
        """测试根据 ID 获取用户."""
        tenant_id = uuid4()

        user = await auth_service.register(
            email="getbyid@example.com",
            password="Password123",
            name="Get By ID",
            tenant_id=tenant_id,
        )

        fetched = await auth_service.get_user_by_id(user.id)

        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.email == "getbyid@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, auth_service: AuthService) -> None:
        """测试根据邮箱获取用户."""
        tenant_id = uuid4()

        await auth_service.register(
            email="getbyemail@example.com",
            password="Password123",
            name="Get By Email",
            tenant_id=tenant_id,
        )

        fetched = await auth_service.get_user_by_email(
            email="getbyemail@example.com",
            tenant_id=tenant_id,
        )

        assert fetched is not None
        assert fetched.email == "getbyemail@example.com"


class TestUserService:
    """UserService 测试."""

    @pytest_asyncio.fixture
    async def user_service(self, db_session: AsyncSession) -> UserService:
        """创建 UserService 实例."""
        return UserService(db_session)

    @pytest.mark.asyncio
    async def test_update_user(self, user_service: UserService) -> None:
        """测试更新用户."""
        from app.domains.auth.services.auth_service import AuthService

        auth_service = AuthService(user_service.db)

        # 创建用户
        tenant_id = uuid4()
        user = await auth_service.register(
            email="update@example.com",
            password="Password123",
            name="Original Name",
            tenant_id=tenant_id,
        )

        # 更新用户
        updated = await user_service.update_user(
            user_id=user.id,
            name="Updated Name",
            phone="1234567890",
            department="New Department",
        )

        assert updated.name == "Updated Name"
        assert updated.phone == "1234567890"
        assert updated.department == "New Department"

    @pytest.mark.asyncio
    async def test_set_user_status(self, user_service: UserService) -> None:
        """测试设置用户状态."""
        from app.domains.auth.services.auth_service import AuthService

        auth_service = AuthService(user_service.db)

        tenant_id = uuid4()
        user = await auth_service.register(
            email="status@example.com",
            password="Password123",
            name="Status Test",
            tenant_id=tenant_id,
        )

        # 禁用用户
        disabled = await user_service.set_user_status(
            user_id=user.id,
            status=UserStatus.DISABLED,
            reason="违反规定",
        )

        assert disabled.status == UserStatus.DISABLED

        # 启用用户
        enabled = await user_service.set_user_status(
            user_id=user.id,
            status=UserStatus.ACTIVE,
        )

        assert enabled.status == UserStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_list_users(self, user_service: UserService) -> None:
        """测试用户列表查询."""
        from app.domains.auth.services.auth_service import AuthService

        auth_service = AuthService(user_service.db)

        tenant_id = uuid4()

        # 创建多个用户
        for i in range(5):
            await auth_service.register(
                email=f"listuser{i}@example.com",
                password="Password123",
                name=f"User {i}",
                tenant_id=tenant_id,
            )

        # 查询列表
        users, total = await user_service.list_users(
            tenant_id=tenant_id,
            page=1,
            page_size=10,
        )

        assert total == 5
        assert len(users) == 5

    @pytest.mark.asyncio
    async def test_list_users_with_role_filter(
        self,
        user_service: UserService,
    ) -> None:
        """测试按角色筛选用户列表."""
        from app.domains.auth.services.auth_service import AuthService

        auth_service = AuthService(user_service.db)

        tenant_id = uuid4()

        # 创建不同角色的用户
        await auth_service.register(
            email="admin@example.com",
            password="Password123",
            name="Admin User",
            tenant_id=tenant_id,
            role=UserRole.ADMIN,
        )
        await auth_service.register(
            email="member@example.com",
            password="Password123",
            name="Member User",
            tenant_id=tenant_id,
            role=UserRole.MEMBER,
        )

        # 按角色筛选
        users, total = await user_service.list_users(
            tenant_id=tenant_id,
            role=UserRole.ADMIN,
        )

        assert total == 1
        assert users[0].role == UserRole.ADMIN
