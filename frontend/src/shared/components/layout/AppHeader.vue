<template>
  <header class="bili-header">
    <div class="header-content">
      <div class="left-entry">
        <a class="logo-container" @click="$router.push('/')">
          <svg class="bili-logo" viewBox="0 0 24 24"></svg>
          <span class="logo-text">IKVCS</span>
        </a>
        <ul class="nav-links">
          <li class="nav-item"><a href="#">首页</a></li>
          <li class="nav-item"><a href="#">番剧</a></li>
          <li class="nav-item"><a href="#">直播</a></li>
        </ul>
      </div>

      <div class="center-search">
        <div class="search-form" :class="{ 'is-focus': isSearchFocused }">
          <input
            v-model="keyword"
            class="search-input"
            placeholder="搜索视频、UP主..."
            @focus="isSearchFocused = true"
            @blur="handleBlur"
            @keyup.enter="handleSearch"
          />
          <div class="search-btn" @click="handleSearch">
            <el-icon><Search /></el-icon>
          </div>
        </div>
      </div>

      <div class="right-entry">
        <div v-if="userStore.isLoggedIn" class="user-avatar-wrap">
          <el-dropdown>
            <el-avatar :src="userStore.avatar" :size="38" class="avatar-img" />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/profile')"
                  >个人中心</el-dropdown-item
                >
                <el-dropdown-item divided @click="handleLogout"
                  >退出登录</el-dropdown-item
                >
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div v-else class="auth-btns">
          <button class="login-btn" @click="$emit('login')">登录</button>
          <button class="reg-btn" @click="$emit('register')">注册</button>
        </div>

        <button
          v-if="userStore.isLoggedIn"
          class="upload-btn"
          @click="handleVideoCenterClick"
        >
          <el-icon><VideoCamera /></el-icon>
          <span>视频中心</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/shared/stores/user";
import { Search, VideoCamera } from "@element-plus/icons-vue";

const router = useRouter();
const userStore = useUserStore();
const keyword = ref("");
const isSearchFocused = ref(false);

const emit = defineEmits(["login", "register"]);

const handleSearch = () => {
  if (!keyword.value.trim()) return;
  router.push({ path: "/search", query: { keyword: keyword.value } });
};

const handleBlur = () => {
  setTimeout(() => (isSearchFocused.value = false), 200);
};

const handleLogout = async () => {
  await userStore.logout();
  location.reload();
};

const handleVideoCenterClick = () => {
  // 检查是否已登录
  if (!userStore.isLoggedIn) {
    // 如果未登录，触发登录事件
    emit('login');
    return;
  }
  
  // 使用命名路由进行跳转，更可靠
  router.push({ name: 'VideoCenter' }).catch((error) => {
    // 如果路由跳转失败（例如路由守卫阻止），记录错误
    console.error('跳转到视频中心失败:', error);
  });
};
</script>

<style lang="scss" scoped>
.bili-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  height: 64px;
  background: var(--bg-white);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: center;

  .header-content {
    width: 100%;
    max-width: var(--container-max-width);
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
}

.left-entry {
  display: flex;
  align-items: center;
  gap: 24px;

  .logo-container {
    display: flex;
    align-items: center;
    cursor: pointer;
    text-decoration: none;
    transition: opacity 0.2s;

    &:hover {
      opacity: 0.8;
    }

    .bili-logo {
      width: 32px;
      height: 32px;
      color: var(--primary-color);
    }
    .logo-text {
      font-size: 20px;
      font-weight: 700;
      color: var(--primary-color);
      margin-left: 8px;
      letter-spacing: -0.5px;
    }
  }

  .nav-links {
    display: flex;
    gap: 20px;
    list-style: none;

    .nav-item {
      a {
        text-decoration: none;
        color: var(--text-primary);
        font-size: 14px;
        font-weight: 500;
        padding: 8px 0;
        transition: color 0.2s;
        position: relative;

        &:hover {
          color: var(--primary-color);
        }

        &::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 0;
          width: 0;
          height: 2px;
          background: var(--primary-color);
          transition: width 0.2s;
        }

        &:hover::after {
          width: 100%;
        }
      }
    }
  }
}

.center-search {
  flex: 1;
  max-width: 500px;
  margin: 0 30px;

  .search-form {
    display: flex;
    align-items: center;
    background-color: var(--bg-global);
    border: 1px solid transparent;
    border-radius: var(--radius-full);
    transition: all 0.2s;
    overflow: hidden;

    &.is-focus {
      background-color: var(--bg-white);
      border-color: var(--primary-color);
      box-shadow: 0 0 0 2px rgba(250, 114, 152, 0.1);
    }

    .search-input {
      flex: 1;
      border: none;
      background: transparent;
      padding: 10px 20px;
      outline: none;
      font-size: 14px;
      color: var(--text-primary);

      &::placeholder {
        color: var(--text-tertiary);
      }
    }

    .search-btn {
      width: 48px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      border-radius: var(--radius-full);
      transition: background 0.2s;
      color: var(--text-tertiary);
      margin-right: 4px;

      &:hover {
        background: var(--border-light);
        color: var(--primary-color);
      }
    }
  }
}

.right-entry {
  display: flex;
  align-items: center;
  gap: 16px;

  .upload-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--primary-color);
    color: #fff;
    border: none;
    padding: 8px 20px;
    border-radius: var(--radius-md);
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    box-shadow: 0 2px 4px rgba(250, 114, 152, 0.2);

    &:hover {
      background: var(--primary-hover);
      box-shadow: 0 4px 8px rgba(250, 114, 152, 0.3);
      transform: translateY(-1px);
    }

    .el-icon {
      font-size: 16px;
    }
  }

  .user-avatar-wrap {
    cursor: pointer;
    transition: transform 0.2s;

    &:hover {
      transform: scale(1.05);
    }

    :deep(.el-avatar) {
      border: 2px solid var(--border-light);
      transition: border-color 0.2s;

      &:hover {
        border-color: var(--primary-color);
      }
    }
  }

  .auth-btns {
    display: flex;
    gap: 12px;

    button {
      padding: 8px 20px;
      border-radius: var(--radius-md);
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: all 0.2s;
      border: none;
    }

    .login-btn {
      background: var(--bg-global);
      color: var(--text-primary);
      
      &:hover {
        background: var(--border-light);
        color: var(--primary-color);
      }
    }

    .reg-btn {
      background: transparent;
      color: var(--text-secondary);
      
      &:hover {
        color: var(--primary-color);
      }
    }
  }
}
</style>

