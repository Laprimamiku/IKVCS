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

        <button class="upload-btn" @click="$router.push('/upload')">
          <el-icon><Upload /></el-icon>
          <span>投稿</span>
        </button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/stores/user";
import { Search, Upload } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

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
</script>

<style lang="scss" scoped>
.bili-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  width: 100%;
  height: 64px;
  background: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
  display: flex;
  justify-content: center;

  .header-content {
    width: 100%;
    max-width: 1600px; // 宽屏适配
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
}

.left-entry {
  display: flex;
  align-items: center;

  .logo-container {
    display: flex;
    align-items: center;
    cursor: pointer;
    margin-right: 20px;

    .bili-logo {
      width: 32px;
      height: 32px;
      color: var(--primary-color);
    }
    .logo-text {
      font-size: 20px;
      font-weight: 800;
      color: var(--primary-color);
      margin-left: 6px;
    }
  }

  .nav-links {
    display: flex;
    gap: 16px;
    list-style: none;

    .nav-item a {
      text-decoration: none;
      color: var(--text-primary);
      font-weight: 500;
      &:hover {
        color: var(--primary-color);
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
    background-color: #f1f2f3;
    border: 1px solid #e3e5e7;
    border-radius: 8px;
    transition: all 0.2s;

    &.is-focus {
      background-color: #fff;
      border-color: #c9ccd0;
    }

    .search-input {
      flex: 1;
      border: none;
      background: transparent;
      padding: 10px 16px;
      outline: none;
      font-size: 14px;
      color: var(--text-primary);
    }

    .search-btn {
      width: 40px;
      height: 32px;
      margin-right: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      border-radius: 6px;
      transition: background 0.2s;

      &:hover {
        background: #e3e5e7;
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
    gap: 4px;
    background: var(--primary-color);
    color: #fff;
    border: none;
    padding: 8px 24px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;

    &:hover {
      background: var(--primary-hover);
    }
  }

  .auth-btns {
    display: flex;
    gap: 12px;

    button {
      padding: 6px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }

    .login-btn {
      background: #e3e5e7;
      color: var(--text-primary);
      border: none;
      &:hover {
        color: var(--primary-color);
      }
    }

    .reg-btn {
      background: transparent;
      border: none;
      color: var(--text-regular);
      &:hover {
        color: var(--primary-color);
      }
    }
  }
}
</style>
