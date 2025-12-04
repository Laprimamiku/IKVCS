<template>
  <div class="home-page">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-wrapper">
        <!-- Logo -->
        <div class="logo" @click="router.push('/')">
          <svg class="logo-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.907l.027-.027c.267-.249.573-.373.92-.373.347 0 .653.124.92.373L9.653 4.44c.071.071.134.142.187.213h4.267a.836.836 0 0 1 .16-.213l2.853-2.747c.267-.249.573-.373.92-.373.347 0 .662.151.929.4.267.249.391.551.391.907 0 .355-.124.657-.373.906zM5.333 7.24c-.746.018-1.373.276-1.88.773-.506.498-.769 1.13-.786 1.894v7.52c.017.764.28 1.395.786 1.893.507.498 1.134.756 1.88.773h13.334c.746-.017 1.373-.275 1.88-.773.506-.498.769-1.129.786-1.893v-7.52c-.017-.765-.28-1.396-.786-1.894-.507-.497-1.134-.755-1.88-.773zM8 11.107c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c0-.373.129-.689.386-.947.258-.257.574-.386.947-.386zm8 0c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c.017-.391.15-.711.4-.96.249-.249.56-.373.933-.373Z"/>
          </svg>
          <span class="logo-text">IKVCS</span>
        </div>

        <!-- 搜索框 -->
        <div class="search-box">
          <input 
            v-model="searchKeyword"
            type="text" 
            class="search-input" 
            placeholder="搜索视频、UP主..."
            @keyup.enter="handleSearch"
            @focus="showSearchPanel = true"
            @blur="handleSearchBlur"
          />
          <button class="search-btn" @click="handleSearch">
            <el-icon><Search /></el-icon>
          </button>
          
          <!-- 搜索下拉面板 -->
          <div v-show="showSearchPanel" class="search-dropdown">
            <!-- 搜索历史 -->
            <div v-if="searchHistory.length" class="search-section">
              <div class="section-header">
                <span>搜索历史</span>
                <el-button text size="small" @click="clearHistory">
                  清空
                </el-button>
              </div>
              <div class="history-list">
                <span
                  v-for="(item, index) in searchHistory"
                  :key="index"
                  class="history-item"
                  @click="selectHistory(item)"
                >
                  {{ item }}
                </span>
              </div>
            </div>
            
            <!-- 热搜榜 -->
            <div class="search-section">
              <div class="section-header">
                <span>热搜榜</span>
              </div>
              <div class="trending-list">
                <div
                  v-for="(item, index) in trendingSearches"
                  :key="index"
                  class="trending-item"
                  @click="selectTrending(item)"
                >
                  <span class="rank" :class="{ 'rank-top': index < 3 }">
                    {{ index + 1 }}
                  </span>
                  <span class="keyword">{{ item }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧用户区 -->
        <div class="user-actions">
          <template v-if="userStore.isLoggedIn">
            <el-dropdown trigger="click" @command="handleCommand">
              <div class="user-info">
                <el-avatar :src="userStore.avatar" :size="32" />
                <span class="user-name">{{ userStore.nickname }}</span>
                <el-icon><ArrowDown /></el-icon>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">
                    <el-icon><User /></el-icon> 个人中心
                  </el-dropdown-item>
                  <el-dropdown-item divided command="logout">
                    <el-icon><SwitchButton /></el-icon> 退出登录
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
          <template v-else>
            <el-button type="primary" size="small" @click="showAuthDialog('login')">登录</el-button>
            <el-button size="small" @click="showAuthDialog('register')">注册</el-button>
          </template>
        </div>
      </div>
    </header>


    <!-- 分类导航 -->
    <nav class="category-nav">
      <div class="nav-wrapper">
        <div 
          v-for="cat in categories" 
          :key="cat.id"
          class="nav-item"
          :class="{ 'is-active': currentCategory === cat.id }"
          @click="selectCategory(cat.id)"
        >
          <el-icon><component :is="cat.icon" /></el-icon>
          <span>{{ cat.name }}</span>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-container">
        <!-- 轮播图 -->
        <HomeBanner 
          :banners="banners"
          @click="handleBannerClick"
        />

        <!-- 视频区域 -->
        <div class="video-section">
          <h2 class="section-title">推荐视频</h2>
          <VideoGrid
            :videos="mockVideos"
            :loading="loading"
            :has-more="hasMore"
            @load-more="loadMoreVideos"
            @video-click="handleVideoClick"
            @watch-later="handleWatchLater"
          />
        </div>
      </div>
    </main>

    <!-- 登录注册弹窗 -->
    <AuthDialog 
      v-model="authDialogVisible" 
      :mode="authMode"
      @success="handleAuthSuccess"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Search, User, ArrowDown, SwitchButton,
  Star, Film, Reading, Monitor, Headset, TrophyBase
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import AuthDialog from '@/components/AuthDialog.vue'
import HomeBanner from '@/components/home/HomeBanner.vue'
import VideoGrid from '@/components/video/VideoGrid.vue'

const router = useRouter()
const userStore = useUserStore()

// 搜索相关
const searchKeyword = ref('')
const showSearchPanel = ref(false)
const searchHistory = ref(['Vue 3 教程', 'Element Plus', '前端开发'])
const trendingSearches = ref([
  'AI 技术解析',
  'Vue 3 新特性',
  '前端性能优化',
  'TypeScript 入门',
  'React vs Vue',
  'Web3.0 趋势',
  '微前端架构',
  'Vite 构建工具',
  'CSS 动画技巧',
  'JavaScript 设计模式'
])

// 分类相关
const currentCategory = ref('all')
const categories = reactive([
  { id: 'all', name: '推荐', icon: Star },
  { id: 'video', name: '视频', icon: Film },
  { id: 'article', name: '专栏', icon: Reading },
  { id: 'live', name: '直播', icon: Monitor },
  { id: 'music', name: '音乐', icon: Headset },
  { id: 'game', name: '游戏', icon: TrophyBase }
])

// 轮播图数据
const banners = ref([
  {
    id: 1,
    title: '精彩视频推荐',
    description: '发现更多优质内容',
    image: 'https://picsum.photos/1400/400?random=1',
    link: '/video/1'
  },
  {
    id: 2,
    title: '热门番剧',
    description: '追番必看',
    image: 'https://picsum.photos/1400/400?random=2',
    link: '/bangumi/1'
  },
  {
    id: 3,
    title: '音乐专区',
    description: '聆听美妙旋律',
    image: 'https://picsum.photos/1400/400?random=3',
    link: '/music/1'
  }
])

// 视频数据
const loading = ref(false)
const hasMore = ref(true)
const mockVideos = reactive([
  { 
    id: 1, 
    title: '【科普】量子计算机的工作原理详解', 
    duration: '12:34', 
    cover: 'https://picsum.photos/400/250?random=1',
    author: { 
      name: 'UP主1', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
      verified: true,
      verifiedType: 'personal'
    }, 
    views: 102000, 
    danmaku: 1234,
    tags: ['4K', '热门'],
    publishTime: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 2, 
    title: '【教程】Vue 3 从入门到精通完整教程', 
    duration: '45:12', 
    cover: 'https://picsum.photos/400/250?random=2',
    author: { 
      name: 'UP主2', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
      verified: false
    }, 
    views: 85000, 
    danmaku: 892,
    tags: ['最新'],
    publishTime: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 3, 
    title: '【科技】AI 如何改变我们的生活方式', 
    duration: '23:45', 
    cover: 'https://picsum.photos/400/250?random=3',
    author: { 
      name: 'UP主3', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png',
      verified: true,
      verifiedType: 'enterprise'
    }, 
    views: 156000, 
    danmaku: 2341,
    tags: ['独家'],
    publishTime: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 4, 
    title: '【编程】Python 数据分析实战项目', 
    duration: '34:56', 
    cover: 'https://picsum.photos/400/250?random=4',
    author: { 
      name: 'UP主4', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' 
    }, 
    views: 68000, 
    danmaku: 567,
    publishTime: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 5, 
    title: '【知识】宇宙的起源与演化历程', 
    duration: '28:30', 
    cover: 'https://picsum.photos/400/250?random=5',
    author: { 
      name: 'UP主5', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' 
    }, 
    views: 123000, 
    danmaku: 1567,
    publishTime: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 6, 
    title: '【技术】区块链技术原理详细讲解', 
    duration: '19:45', 
    cover: 'https://picsum.photos/400/250?random=6',
    author: { 
      name: 'UP主6', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' 
    }, 
    views: 91000, 
    danmaku: 734,
    publishTime: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 7, 
    title: '【动画】精彩动画短片合集推荐', 
    duration: '15:20', 
    cover: 'https://picsum.photos/400/250?random=7',
    author: { 
      name: 'UP主7', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' 
    }, 
    views: 205000, 
    danmaku: 3456,
    publishTime: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString()
  },
  { 
    id: 8, 
    title: '【音乐】经典钢琴曲演奏欣赏', 
    duration: '08:15', 
    cover: 'https://picsum.photos/400/250?random=8',
    author: { 
      name: 'UP主8', 
      avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' 
    }, 
    views: 52000, 
    danmaku: 234,
    publishTime: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString()
  }
])

// 认证弹窗
const authDialogVisible = ref(false)
const authMode = ref('login')

onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try {
      await userStore.initUserInfo()
    } catch (error) {
      console.error('初始化用户信息失败:', error)
    }
  }
})

// 搜索相关方法
const handleSearch = () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  
  // 添加到搜索历史
  if (!searchHistory.value.includes(searchKeyword.value)) {
    searchHistory.value.unshift(searchKeyword.value)
    if (searchHistory.value.length > 10) {
      searchHistory.value.pop()
    }
  }
  
  console.log('搜索:', searchKeyword.value)
  showSearchPanel.value = false
}

const handleSearchBlur = () => {
  // 延迟关闭，以便点击事件能够触发
  setTimeout(() => {
    showSearchPanel.value = false
  }, 200)
}

const selectHistory = (keyword) => {
  searchKeyword.value = keyword
  handleSearch()
}

const selectTrending = (keyword) => {
  searchKeyword.value = keyword
  handleSearch()
}

const clearHistory = () => {
  searchHistory.value = []
}

// 分类相关方法
const selectCategory = (categoryId) => {
  currentCategory.value = categoryId
  console.log('选择分类:', categoryId)
}

// 轮播图相关方法
const handleBannerClick = (banner) => {
  console.log('点击轮播图:', banner)
  if (banner.link) {
    router.push(banner.link)
  }
}

// 视频相关方法
const handleVideoClick = (video) => {
  console.log('点击视频:', video)
  // router.push(`/video/${video.id}`)
}

const handleWatchLater = (video) => {
  console.log('稍后再看:', video)
}

const loadMoreVideos = async () => {
  loading.value = true
  
  // 模拟加载更多
  setTimeout(() => {
    const newVideos = Array.from({ length: 8 }, (_, i) => ({
      id: mockVideos.length + i + 1,
      title: `新视频 ${mockVideos.length + i + 1}`,
      duration: '10:00',
      cover: `https://picsum.photos/400/250?random=${mockVideos.length + i + 1}`,
      author: {
        name: `UP主${mockVideos.length + i + 1}`,
        avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png'
      },
      views: Math.floor(Math.random() * 100000),
      danmaku: Math.floor(Math.random() * 1000),
      publishTime: new Date().toISOString()
    }))
    
    mockVideos.push(...newVideos)
    loading.value = false
    
    // 模拟没有更多数据
    if (mockVideos.length >= 40) {
      hasMore.value = false
    }
  }, 1000)
}

// 认证相关方法
const showAuthDialog = (mode) => {
  authMode.value = mode
  authDialogVisible.value = true
}

const handleAuthSuccess = () => {
  console.log('登录注册成功')
}

const handleCommand = async (command) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      })
      await userStore.logout()
      ElMessage.success('退出登录成功')
      location.reload()
    } catch (error) {
      if (error !== 'cancel') {
        console.error('退出登录失败:', error)
      }
    }
  }
}
</script>


<style scoped>
.home-page {
  min-height: 100vh;
  background: var(--bg-light);
}

/* ==================== 顶部导航栏 ==================== */
.app-header {
  background: var(--bg-white);
  box-shadow: var(--shadow-sm);
  position: sticky;
  top: 0;
  z-index: var(--z-index-sticky);
}

.header-wrapper {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  height: var(--header-height);
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  flex-shrink: 0;
  transition: transform var(--transition-fast);
}

.logo:hover {
  transform: scale(1.05);
}

.logo-icon {
  width: 32px;
  height: 32px;
  color: var(--primary-color);
}

.logo-text {
  font-size: var(--font-size-xl);
  font-weight: bold;
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 搜索框 */
.search-box {
  position: relative;
  flex: 1;
  max-width: 500px;
}

.search-box input,
.search-box button {
  border: none;
  outline: none;
  background: transparent;
}

.search-box {
  display: flex;
  background: var(--bg-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--transition-base);
}

.search-box:focus-within {
  background: var(--bg-white);
  box-shadow: 0 0 0 2px var(--primary-light);
}

.search-input {
  flex: 1;
  padding: var(--spacing-sm) var(--spacing-md);
  font-size: var(--font-size-base);
  color: var(--text-primary);
}

.search-input::placeholder {
  color: var(--text-placeholder);
}

.search-btn {
  padding: var(--spacing-sm) var(--spacing-md);
  color: var(--text-secondary);
  cursor: pointer;
  transition: color var(--transition-fast);
}

.search-btn:hover {
  color: var(--primary-color);
}

/* 搜索下拉面板 */
.search-dropdown {
  position: absolute;
  top: calc(100% + var(--spacing-sm));
  left: 0;
  right: 0;
  background: var(--bg-white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  padding: var(--spacing-md);
  z-index: var(--z-index-dropdown);
  animation: fadeInUp 0.3s ease;
}

.search-section {
  margin-bottom: var(--spacing-md);
}

.search-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-regular);
}

.history-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.history-item {
  padding: var(--spacing-xs) var(--spacing-base);
  background: var(--bg-light);
  border-radius: var(--radius-base);
  font-size: var(--font-size-sm);
  color: var(--text-regular);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.history-item:hover {
  background: var(--primary-light);
  color: var(--primary-color);
}

.trending-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.trending-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.trending-item:hover {
  background: var(--bg-light);
}

.rank {
  width: 20px;
  text-align: center;
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--text-secondary);
}

.rank-top {
  color: var(--primary-color);
  font-weight: bold;
}

.keyword {
  flex: 1;
  font-size: var(--font-size-sm);
  color: var(--text-regular);
}

/* 用户操作区 */
.user-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-base);
  flex-shrink: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) var(--spacing-base);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.user-info:hover {
  background: var(--bg-light);
}

.user-name {
  font-size: var(--font-size-base);
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ==================== 分类导航 ==================== */
.category-nav {
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: var(--header-height);
  z-index: calc(var(--z-index-sticky) - 1);
}

.nav-wrapper {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
  display: flex;
  gap: var(--spacing-2xl);
  overflow-x: auto;
  scrollbar-width: none;
}

.nav-wrapper::-webkit-scrollbar {
  display: none;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-md) 0;
  font-size: var(--font-size-base);
  color: var(--text-regular);
  cursor: pointer;
  position: relative;
  white-space: nowrap;
  transition: color var(--transition-fast);
}

.nav-item:hover {
  color: var(--primary-color);
}

.nav-item.is-active {
  color: var(--primary-color);
  font-weight: 500;
}

.nav-item.is-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary-color);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

/* ==================== 主内容区 ==================== */
.main-content {
  padding: var(--spacing-lg) 0;
}

.content-container {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}

/* 视频区域 */
.video-section {
  margin-top: var(--spacing-xl);
}

.section-title {
  font-size: var(--font-size-xl);
  font-weight: 600;
  margin-bottom: var(--spacing-md);
  color: var(--text-primary);
}

/* ==================== 响应式设计 ==================== */
@media (max-width: 768px) {
  .header-wrapper {
    padding: 0 var(--spacing-md);
    gap: var(--spacing-md);
  }
  
  .search-box {
    max-width: none;
  }
  
  .user-name {
    display: none;
  }
  
  .nav-wrapper {
    padding: 0 var(--spacing-md);
    gap: var(--spacing-lg);
  }
  
  .content-container {
    padding: 0 var(--spacing-md);
  }
}
</style>
