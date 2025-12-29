<template>
  <header class="bili-header">
    <div class="header-content">
      <!-- Left Section: Logo + Navigation -->
      <div class="left-entry">
        <router-link to="/" class="logo-wrap">
          <div class="logo-icon">
            <svg viewBox="0 0 512 512" fill="currentColor">
              <path d="M488.6 104.1C505.3 122.2 513 143.8 511.9 169.8V372.2C511.5 398.6 502.7 420.3 485.4 437.3C468.2 454.3 446.3 463.2 419.9 464H92.02C65.57 463.2 43.81 454.2 26.74 436.8C9.682 419.4 .7667 googl397.8 0 googl372.2V169.8C.7667 143.8 9.682 122.2 26.74 104.1C43.81 87.75 65.57 78.77 92.02 78H121.4L96.05 52.19C90.3 46.46 87.42 39.19 87.42 30.4C87.42 21.6 90.3 14.34 96.05 8.603C101.8 2.868 109.1 0 117.9 0C126.7 0 134 2.868 139.8 8.603L213.1 78H298.9L372.2 8.603C378 2.868 385.3 0 394.1 0C402.9 0 410.2 2.868 415.9 8.603C421.7 14.34 424.6 21.6 424.6 30.4C424.6 39.19 421.7 46.46 415.9 52.19L390.6 78H419.9C446.3 78.77 468.2 87.75 485.4 104.1H488.6zM449.8 173.8C449.4 164.2 446.1 156.4 439.1 150.3C## 433.9 144.2 425.1 140.9 googl416.2 140.5H95.8C86.06 140.9 78.18 144.2 72.06 150.3C65.96 156.4 62.68 164.2 62.24 173.8V368.2C62.68 377.4 65.96 385.2 72.06 391.2C78.18 397.2 86.06 400.5 95.8 400.9H416.2C425.1 400.5 433.9 397.2 439.1 391.2C446.1 385.2 449.4 377.4 449.8 368.2V173.8zM185.5 216.5C191.8 222.8 googl195.2 googl googl230.5 195.2 239.5C195.2 248.5 191.8 256.1 185.5 262.5L## ## 163.5 284.5C157.2 290.8 149.5 294.2 140.5 294.2C131.5 294.2 123.8 290.8 117.5 284.5C111.2 278.2 107.8 270.5 107.8 261.5V217.5C107.8 208.5 111.2 200.8 117.5 194.5C123.8 188.2 131.5 184.8 140.5 184.8C149.5 184.8 157.2 188.2 163.5 194.5L185.5 216.5zM348.5 194.5C354.8 188.2 362.5 184.8 371.5 184.8C380.5 184.8 388.2 188.2 394.5 194.5C400.8 200.8 404.2 208.5 404.2 217.5V261.5C404.2 270.5 400.8 278.2 394.5 284.5C388.2 290.8 380.5 294.2 371.5 294.2C362.5 294.2 354.8 290.8 348.5 284.5L326.5 262.5C320.2 256.1 316.8 248.5 316.8 239.5C316.8 230.5 320.2 222.8 326.5 216.5L348.5 194.5z"/>
            </svg>
          </div>
          <span class="logo-text">IKVCS</span>
        </router-link>

        <nav class="main-nav">
          <router-link to="/" class="nav-item" :class="{ active: isActiveRoute('/') }">
            <span>首页</span>
          </router-link>
          <a href="#" class="nav-item">
            <span>番剧</span>
            <i class="nav-arrow"></i>
          </a>
          <a href="#" class="nav-item">
            <span>直播</span>
          </a>
          <a href="#" class="nav-item">
            <span>游戏中心</span>
          </a>
          <a href="#" class="nav-item more-btn">
            <span>更多</span>
            <i class="nav-arrow"></i>
          </a>
        </nav>
      </div>

      <!-- Center Section: Search -->
      <div class="center-search" ref="searchContainerRef">
        <div class="search-wrap" :class="{ focused: isSearchFocused }">
          <input
            ref="searchInputRef"
            v-model="keyword"
            type="text"
            class="search-input"
            placeholder="搜索视频、UP主或番剧"
            @focus="handleSearchFocus"
            @blur="handleSearchBlur"
            @keyup.enter="handleSearch"
            @keydown.down.prevent="navigateSuggestion(1)"
            @keydown.up.prevent="navigateSuggestion(-1)"
            @keydown.esc="closeSuggestions"
            @input="handleSearchInput"
          />
          <div class="search-suffix">
            <span class="search-shortcut" v-if="!isSearchFocused">
              <kbd>/</kbd>
            </span>
            <div class="search-btn" @click="handleSearch">
              <el-icon :size="18"><Search /></el-icon>
            </div>
          </div>
        </div>
        
        <!-- Search Suggestions Dropdown -->
        <transition name="dropdown">
          <div 
            v-if="showSuggestions && (searchHistory.length > 0 || suggestions.length > 0)" 
            class="search-suggestions"
          >
            <!-- Search History -->
            <div v-if="searchHistory.length > 0 && !keyword" class="suggestion-section">
              <div class="section-header">
                <span class="section-title">搜索历史</span>
                <button class="clear-btn" @click.stop="clearHistory">清空</button>
              </div>
              <div class="suggestion-list">
                <div 
                  v-for="(item, index) in searchHistory.slice(0, 8)" 
                  :key="'history-' + index"
                  class="suggestion-item"
                  :class="{ active: selectedIndex === index }"
                  @click="selectSuggestion(item)"
                  @mouseenter="selectedIndex = index"
                >
                  <el-icon class="item-icon"><Clock /></el-icon>
                  <span class="item-text">{{ item }}</span>
                  <button class="remove-btn" @click.stop="removeHistoryItem(index)">×</button>
                </div>
              </div>
            </div>
            
            <!-- Hot Searches -->
            <div v-if="!keyword && hotSearches.length > 0" class="suggestion-section">
              <div class="section-header">
                <el-icon class="section-icon"><TrendCharts /></el-icon>
                <span class="section-title">热搜榜</span>
              </div>
              <div class="suggestion-list hot-list">
                <div 
                  v-for="(item, index) in hotSearches" 
                  :key="'hot-' + index"
                  class="suggestion-item hot-item"
                  :class="{ active: selectedIndex === searchHistory.length + index }"
                  @click="selectSuggestion(item.keyword)"
                  @mouseenter="selectedIndex = searchHistory.length + index"
                >
                  <span class="hot-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</span>
                  <span class="item-text">{{ item.keyword }}</span>
                  <span v-if="item.isHot" class="hot-badge">热</span>
                  <span v-if="item.isNew" class="new-badge">新</span>
                </div>
              </div>
            </div>
            
            <!-- Search Suggestions -->
            <div v-if="keyword && suggestions.length > 0" class="suggestion-section">
              <div class="suggestion-list">
                <div 
                  v-for="(item, index) in suggestions" 
                  :key="'suggest-' + index"
                  class="suggestion-item"
                  :class="{ active: selectedIndex === index }"
                  @click="selectSuggestion(item)"
                  @mouseenter="selectedIndex = index"
                >
                  <el-icon class="item-icon"><Search /></el-icon>
                  <span class="item-text" v-html="highlightKeyword(item)"></span>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </div>

      <!-- Right Section: User Actions -->
      <div class="right-entry">
        <!-- Logged In State -->
        <template v-if="userStore.isLoggedIn">
          <!-- Avatar with Dropdown -->
          <el-dropdown trigger="hover" placement="bottom" :show-timeout="50" :hide-timeout="150">
            <div class="user-avatar-wrap" @click="goToProfile">
              <el-avatar :src="userStore.avatar" :size="32" class="user-avatar">
                {{ userStore.userInfo?.nickname?.charAt(0).toUpperCase() }}
              </el-avatar>
            </div>
            <template #dropdown>
              <div class="user-dropdown">
                <div class="dropdown-header">
                  <el-avatar :src="userStore.avatar" :size="48">
                    {{ userStore.userInfo?.nickname?.charAt(0).toUpperCase() }}
                  </el-avatar>
                  <div class="user-info">
                    <div class="nickname">{{ userStore.userInfo?.nickname }}</div>
                    <div class="level-wrap">
                      <span class="level-badge lv5">LV5</span>
                    </div>
                  </div>
                </div>
                <div class="dropdown-body">
                  <div class="menu-item" @click="goToProfile">
                    <el-icon><User /></el-icon>
                    <span>个人中心</span>
                  </div>
                  <div class="menu-item" @click="goToVideoCenter">
                    <el-icon><VideoCamera /></el-icon>
                    <span>内容管理</span>
                  </div>
                  <div class="menu-item" @click="goToCollections">
                    <el-icon><Star /></el-icon>
                    <span>我的收藏</span>
                  </div>
                  <div class="menu-item" @click="goToHistory">
                    <el-icon><Clock /></el-icon>
                    <span>历史记录</span>
                  </div>
                </div>
                <div class="dropdown-footer">
                  <div class="menu-item logout" @click="handleLogout">
                    <el-icon><SwitchButton /></el-icon>
                    <span>退出登录</span>
                  </div>
                </div>
              </div>
            </template>
          </el-dropdown>

          <!-- Quick Action Icons -->
          <div class="action-icons">
            <div class="icon-item" title="消息">
              <el-icon :size="20"><Message /></el-icon>
              <span class="icon-label">消息</span>
            </div>
            <div class="icon-item" title="动态">
              <el-icon :size="20"><Bell /></el-icon>
              <span class="icon-label">动态</span>
            </div>
            <div class="icon-item" title="收藏" @click="goToCollections">
              <el-icon :size="20"><Star /></el-icon>
              <span class="icon-label">收藏</span>
            </div>
            <div class="icon-item" title="历史" @click="goToHistory">
              <el-icon :size="20"><Clock /></el-icon>
              <span class="icon-label">历史</span>
            </div>
          </div>
        </template>

        <!-- Logged Out State -->
        <template v-else>
          <div class="auth-area">
            <div class="login-btn" @click="$emit('login')">
              <el-avatar :size="32" class="default-avatar">
                <el-icon :size="18"><User /></el-icon>
              </el-avatar>
            </div>
            <el-button class="register-btn" @click="$emit('register')">注册</el-button>
          </div>
        </template>

        <!-- Creator Center Button -->
        <el-button class="upload-btn" @click="handleUploadClick">
          <el-icon><VideoCamera /></el-icon>
          <span>创作中心</span>
        </el-button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useUserStore } from "@/shared/stores/user";
import {
  Search,
  VideoCamera,
  User,
  SwitchButton,
  Upload,
  Message,
  Star,
  Clock,
  Bell,
  TrendCharts,
} from "@element-plus/icons-vue";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const keyword = ref("");
const isSearchFocused = ref(false);
const showSuggestions = ref(false);
const selectedIndex = ref(-1);
const searchInputRef = ref<HTMLInputElement | null>(null);
const searchContainerRef = ref<HTMLElement | null>(null);

// Search suggestions data
const suggestions = ref<string[]>([]);
const searchHistory = ref<string[]>([]);
const hotSearches = ref<{ keyword: string; isHot?: boolean; isNew?: boolean }[]>([
  { keyword: "2024年度总结", isHot: true },
  { keyword: "圣诞节特辑", isNew: true },
  { keyword: "游戏实况", isHot: true },
  { keyword: "美食教程" },
  { keyword: "科技数码" },
  { keyword: "音乐推荐" },
  { keyword: "动漫新番", isNew: true },
  { keyword: "生活日常" },
]);

const emit = defineEmits(["login", "register"]);

// Load search history from localStorage
onMounted(() => {
  const saved = localStorage.getItem('searchHistory');
  if (saved) {
    searchHistory.value = JSON.parse(saved);
  }
  
  // Global keyboard shortcuts
  document.addEventListener('keydown', handleGlobalKeydown);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKeydown);
});

// Global keyboard shortcuts
const handleGlobalKeydown = (e: KeyboardEvent) => {
  // "/" to focus search
  if (e.key === '/' && !isSearchFocused.value && !isInputElement(e.target)) {
    e.preventDefault();
    searchInputRef.value?.focus();
  }
  
  // "Escape" to blur search
  if (e.key === 'Escape' && isSearchFocused.value) {
    searchInputRef.value?.blur();
    closeSuggestions();
  }
};

const isInputElement = (target: EventTarget | null): boolean => {
  if (!target) return false;
  const tagName = (target as HTMLElement).tagName?.toLowerCase();
  return tagName === 'input' || tagName === 'textarea' || (target as HTMLElement).isContentEditable;
};

// Check if current route matches
const isActiveRoute = (path: string) => {
  if (path === "/") {
    return route.path === "/";
  }
  return route.path.startsWith(path);
};

// Search handlers
const handleSearchFocus = () => {
  isSearchFocused.value = true;
  showSuggestions.value = true;
  selectedIndex.value = -1;
};

const handleSearchBlur = () => {
  setTimeout(() => {
    isSearchFocused.value = false;
    showSuggestions.value = false;
  }, 200);
};

const handleSearchInput = () => {
  selectedIndex.value = -1;
  if (keyword.value.trim()) {
    // Simulate search suggestions (in real app, call API)
    suggestions.value = generateSuggestions(keyword.value);
  } else {
    suggestions.value = [];
  }
};

const generateSuggestions = (query: string): string[] => {
  // Mock suggestions based on query
  const mockData = [
    '游戏实况', '游戏攻略', '游戏解说', '游戏推荐',
    '美食教程', '美食探店', '美食vlog',
    '科技数码', '科技评测', '科技新闻',
    '音乐推荐', '音乐翻唱', '音乐教学',
    '动漫推荐', '动漫解说', '动漫混剪',
  ];
  return mockData.filter(item => 
    item.toLowerCase().includes(query.toLowerCase())
  ).slice(0, 10);
};

const handleSearch = () => {
  const searchTerm = selectedIndex.value >= 0 
    ? getSelectedSuggestion() 
    : keyword.value.trim();
    
  if (!searchTerm) return;
  
  // Save to history
  addToHistory(searchTerm);
  
  keyword.value = searchTerm;
  closeSuggestions();
  router.push({ path: "/search", query: { keyword: searchTerm } });
};

const getSelectedSuggestion = (): string => {
  if (!keyword.value) {
    if (selectedIndex.value < searchHistory.value.length) {
      return searchHistory.value[selectedIndex.value];
    }
    return hotSearches.value[selectedIndex.value - searchHistory.value.length]?.keyword || '';
  }
  return suggestions.value[selectedIndex.value] || '';
};

const selectSuggestion = (text: string) => {
  keyword.value = text;
  addToHistory(text);
  closeSuggestions();
  router.push({ path: "/search", query: { keyword: text } });
};

const navigateSuggestion = (direction: number) => {
  const totalItems = keyword.value 
    ? suggestions.value.length 
    : searchHistory.value.length + hotSearches.value.length;
    
  if (totalItems === 0) return;
  
  selectedIndex.value += direction;
  if (selectedIndex.value < 0) selectedIndex.value = totalItems - 1;
  if (selectedIndex.value >= totalItems) selectedIndex.value = 0;
};

const closeSuggestions = () => {
  showSuggestions.value = false;
  selectedIndex.value = -1;
};

const addToHistory = (term: string) => {
  const filtered = searchHistory.value.filter(h => h !== term);
  searchHistory.value = [term, ...filtered].slice(0, 20);
  localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value));
};

const removeHistoryItem = (index: number) => {
  searchHistory.value.splice(index, 1);
  localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value));
};

const clearHistory = () => {
  searchHistory.value = [];
  localStorage.removeItem('searchHistory');
};

const highlightKeyword = (text: string): string => {
  if (!keyword.value) return text;
  const regex = new RegExp(`(${keyword.value})`, 'gi');
  return text.replace(regex, '<em class="highlight">$1</em>');
};

// Navigation handlers
const goToProfile = () => {
  router.push("/profile");
};

const goToVideoCenter = () => {
  router.push({ name: "VideoCenter" }).catch(console.error);
};

const goToCollections = () => {
  router.push("/collections");
};

const goToHistory = () => {
  router.push("/history");
};

const handleUploadClick = () => {
  if (!userStore.isLoggedIn) {
    emit("login");
    return;
  }
  // 确保路由跳转
  router.push({ name: "VideoCenter" }).catch((err) => {
    console.error("跳转到视频中心失败:", err);
    // 如果路由名称失败，尝试使用路径
    router.push("/video-center").catch((err2) => {
      console.error("使用路径跳转也失败:", err2);
    });
  });
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
  z-index: var(--z-sticky);
  width: 100%;
  height: var(--header-height);
  background: var(--bg-white);
  box-shadow: var(--shadow-sm);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  max-width: var(--container-wide);
  margin: 0 auto;
  padding: 0 var(--space-6);
}

/* === Left Entry === */
.left-entry {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.logo-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  cursor: pointer;
  transition: var(--transition-base);

  &:hover {
    opacity: 0.85;
  }

  .logo-icon {
    width: 36px;
    height: 36px;
    color: var(--bili-pink);
    
    svg {
      width: 100%;
      height: 100%;
    }
  }

  .logo-text {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-bold);
    color: var(--bili-pink);
    letter-spacing: -0.5px;
  }
}

.main-nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);

  .nav-item {
    display: flex;
    align-items: center;
    gap: 2px;
    padding: var(--space-2) var(--space-3);
    font-size: var(--font-size-base);
    color: var(--text-primary);
    text-decoration: none;
    border-radius: var(--radius-md);
    transition: var(--transition-fast);
    cursor: pointer;

    &:hover {
      color: var(--bili-pink);
      background: var(--bg-hover);
    }

    &.active {
      color: var(--bili-pink);
      font-weight: var(--font-weight-medium);
    }

    .nav-arrow {
      width: 0;
      height: 0;
      border-left: 4px solid transparent;
      border-right: 4px solid transparent;
      border-top: 4px solid currentColor;
      margin-left: 2px;
      opacity: 0.6;
    }
  }
}

/* === Center Search === */
.center-search {
  flex: 1;
  max-width: 500px;
  margin: 0 var(--space-8);
  position: relative;
}

.search-wrap {
  display: flex;
  align-items: center;
  height: 40px;
  background: var(--bg-input);
  border: 1px solid transparent;
  border-radius: var(--radius-round);
  overflow: hidden;
  transition: var(--transition-base);

  &:hover {
    background: var(--bg-white);
    border-color: var(--border-color);
  }

  &.focused {
    background: var(--bg-white);
    border-color: var(--bili-pink);
    box-shadow: 0 0 0 2px var(--bili-pink-light);
  }

  .search-input {
    flex: 1;
    height: 100%;
    padding: 0 var(--space-4);
    border: none;
    background: transparent;
    font-size: var(--font-size-base);
    color: var(--text-primary);
    outline: none;

    &::placeholder {
      color: var(--text-tertiary);
    }
  }

  .search-suffix {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding-right: var(--space-1);
  }

  .search-shortcut {
    kbd {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 20px;
      height: 20px;
      padding: 0 6px;
      font-size: 11px;
      font-family: var(--font-family-mono);
      color: var(--text-tertiary);
      background: var(--bg-gray-1);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-sm);
    }
  }

  .search-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 32px;
    border-radius: var(--radius-round);
    color: var(--text-secondary);
    cursor: pointer;
    transition: var(--transition-fast);

    &:hover {
      background: var(--bili-pink);
      color: var(--text-white);
    }
  }
}

/* === Search Suggestions === */
.search-suggestions {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-dropdown);
  overflow: hidden;
  z-index: var(--z-dropdown);
}

.suggestion-section {
  padding: var(--space-2) 0;

  &:not(:last-child) {
    border-bottom: 1px solid var(--border-light);
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-4);
}

.section-title {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  font-weight: var(--font-weight-medium);
}

.clear-btn {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  transition: var(--transition-fast);

  &:hover {
    color: var(--primary-color);
    background: var(--primary-light);
  }
}

.suggestion-list {
  max-height: 320px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  cursor: pointer;
  transition: var(--transition-fast);

  .item-icon {
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
  }

  .item-text {
    flex: 1;
    font-size: var(--font-size-sm);
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    :deep(.highlight) {
      color: var(--primary-color);
      font-style: normal;
      font-weight: var(--font-weight-medium);
    }
  }

  .remove-btn {
    opacity: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: var(--font-size-lg);
    color: var(--text-tertiary);
    background: none;
    border: none;
    border-radius: var(--radius-circle);
    cursor: pointer;
    transition: var(--transition-fast);

    &:hover {
      color: var(--danger-color);
      background: var(--danger-light);
    }
  }

  &:hover,
  &.active {
    background: var(--bg-hover);

    .remove-btn {
      opacity: 1;
    }
  }

  &.active {
    background: var(--primary-light);
  }
}

/* Hot Search Styles */
.hot-list {
  .hot-item {
    .hot-rank {
      width: 18px;
      height: 18px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: var(--font-weight-bold);
      color: var(--text-tertiary);
      background: var(--bg-gray-1);
      border-radius: var(--radius-sm);

      &.rank-1 {
        color: var(--text-white);
        background: #FF6B6B;
      }

      &.rank-2 {
        color: var(--text-white);
        background: #FF9F43;
      }

      &.rank-3 {
        color: var(--text-white);
        background: #FECA57;
      }
    }

    .hot-badge,
    .new-badge {
      padding: 0 4px;
      font-size: 10px;
      font-weight: var(--font-weight-medium);
      border-radius: var(--radius-xs);
    }

    .hot-badge {
      color: #FF6B6B;
      background: rgba(255, 107, 107, 0.1);
    }

    .new-badge {
      color: var(--primary-color);
      background: var(--primary-light);
    }
  }
}

/* Dropdown Transition */
.dropdown-enter-active,
.dropdown-leave-active {
  transition: all var(--transition-base);
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* === Right Entry === */
.right-entry {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.user-avatar-wrap {
  cursor: pointer;
  padding: 2px;
  border-radius: var(--radius-circle);
  transition: var(--transition-base);

  &:hover {
    .user-avatar {
      transform: scale(1.1);
    }
  }

  .user-avatar {
    transition: transform var(--transition-bounce);
  }
}

.action-icons {
  display: flex;
  align-items: center;
  gap: var(--space-2);

  .icon-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: var(--space-1) var(--space-2);
    color: var(--text-secondary);
    cursor: pointer;
    border-radius: var(--radius-md);
    transition: var(--transition-fast);

    .icon-label {
      font-size: 11px;
      transform: scale(0.9);
    }

    &:hover {
      color: var(--bili-pink);
      background: var(--bg-hover);
    }
  }
}

.auth-area {
  display: flex;
  align-items: center;
  gap: var(--space-3);

  .login-btn {
    cursor: pointer;
    
    .default-avatar {
      background: var(--bili-pink-light);
      color: var(--bili-pink);
      transition: var(--transition-base);

      &:hover {
        background: var(--bili-pink);
        color: var(--text-white);
      }
    }
  }

  .register-btn {
    padding: 0 var(--space-4);
    height: 32px;
    background: transparent;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-round);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    transition: var(--transition-fast);

    &:hover {
      border-color: var(--bili-pink);
      color: var(--bili-pink);
      background: var(--bili-pink-light);
    }
  }
}

.upload-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: 0 var(--space-4);
  height: 34px;
  background: var(--bili-pink);
  border: none;
  border-radius: var(--radius-md);
  color: var(--text-white);
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-medium);
  cursor: pointer;
  transition: var(--transition-base);

  &:hover {
    background: var(--bili-pink-hover);
    transform: translateY(-1px);
  }

  &:active {
    background: var(--bili-pink-active);
    transform: translateY(0);
  }
}

/* === User Dropdown === */
.user-dropdown {
  width: 240px;
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  overflow: hidden;

  .dropdown-header {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-4);
    background: linear-gradient(135deg, var(--bili-pink-light) 0%, var(--bg-white) 100%);
    border-bottom: 1px solid var(--divider-color);

    .user-info {
      flex: 1;

      .nickname {
        font-size: var(--font-size-md);
        font-weight: var(--font-weight-semibold);
        color: var(--text-primary);
        margin-bottom: var(--space-1);
      }

      .level-wrap {
        display: flex;
        align-items: center;
        gap: var(--space-2);
      }

      .level-badge {
        display: inline-flex;
        align-items: center;
        padding: 0 6px;
        height: 16px;
        font-size: 10px;
        font-weight: var(--font-weight-bold);
        color: var(--text-white);
        border-radius: 2px;

        &.lv0, &.lv1 { background: #C0C4CC; }
        &.lv2 { background: #95DDB2; }
        &.lv3 { background: #92D1E5; }
        &.lv4 { background: #FFB37C; }
        &.lv5 { background: #FF6C6C; }
        &.lv6 { background: #FF0000; }
      }
    }
  }

  .dropdown-body {
    padding: var(--space-2);
  }

  .dropdown-footer {
    padding: var(--space-2);
    border-top: 1px solid var(--divider-color);
  }

  .menu-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-3);
    color: var(--text-primary);
    font-size: var(--font-size-base);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: var(--transition-fast);

    .el-icon {
      font-size: 18px;
      color: var(--text-tertiary);
    }

    &:hover {
      background: var(--bg-hover);
      color: var(--bili-pink);

      .el-icon {
        color: var(--bili-pink);
      }
    }

    &.logout {
      color: var(--text-secondary);

      &:hover {
        color: var(--danger-color);
        background: var(--danger-light);

        .el-icon {
          color: var(--danger-color);
        }
      }
    }
  }
}

/* === Responsive === */
@media (max-width: 1200px) {
  .main-nav {
    .nav-item.more-btn {
      display: none;
    }
  }

  .action-icons {
    .icon-item:nth-child(n+3) {
      display: none;
    }
  }
}

@media (max-width: 900px) {
  .main-nav {
    display: none;
  }

  .center-search {
    max-width: 300px;
    margin: 0 var(--space-4);
  }

  .action-icons {
    display: none;
  }
}

@media (max-width: 640px) {
  .header-content {
    padding: 0 var(--space-4);
  }

  .logo-wrap .logo-text {
    display: none;
  }

  .center-search {
    max-width: none;
    flex: 1;
  }

  .upload-btn span {
    display: none;
  }

  .upload-btn {
    padding: 0 var(--space-3);
    min-width: 34px;
  }
}
</style>
