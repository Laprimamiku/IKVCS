<template>
  <div class="bili-home">
    <!-- Bilibili 风格顶部导航栏 -->
    <header class="bili-header">
      <div class="bili-header-wrapper">
        <!-- Logo -->
        <div class="bili-logo" @click="router.push('/')">
          <svg class="bili-logo-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M17.813 4.653h.854c1.51.054 2.769.578 3.773 1.574 1.004.995 1.524 2.249 1.56 3.76v7.36c-.036 1.51-.556 2.769-1.56 3.773s-2.262 1.524-3.773 1.56H5.333c-1.51-.036-2.769-.556-3.773-1.56S.036 18.858 0 17.347v-7.36c.036-1.511.556-2.765 1.56-3.76 1.004-.996 2.262-1.52 3.773-1.574h.774l-1.174-1.12a1.234 1.234 0 0 1-.373-.906c0-.356.124-.658.373-.907l.027-.027c.267-.249.573-.373.92-.373.347 0 .653.124.92.373L9.653 4.44c.071.071.134.142.187.213h4.267a.836.836 0 0 1 .16-.213l2.853-2.747c.267-.249.573-.373.92-.373.347 0 .662.151.929.4.267.249.391.551.391.907 0 .355-.124.657-.373.906zM5.333 7.24c-.746.018-1.373.276-1.88.773-.506.498-.769 1.13-.786 1.894v7.52c.017.764.28 1.395.786 1.893.507.498 1.134.756 1.88.773h13.334c.746-.017 1.373-.275 1.88-.773.506-.498.769-1.129.786-1.893v-7.52c-.017-.765-.28-1.396-.786-1.894-.507-.497-1.134-.755-1.88-.773zM8 11.107c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c0-.373.129-.689.386-.947.258-.257.574-.386.947-.386zm8 0c.373 0 .684.124.933.373.25.249.383.569.4.96v1.173c-.017.391-.15.711-.4.96-.249.25-.56.374-.933.374s-.684-.125-.933-.374c-.25-.249-.383-.569-.4-.96V12.44c.017-.391.15-.711.4-.96.249-.249.56-.373.933-.373Z"/>
          </svg>
          <span class="bili-logo-text">IKVCS</span>
        </div>

        <!-- 搜索框 -->
        <div class="bili-search-box">
          <input 
            v-model="searchKeyword"
            type="text" 
            class="bili-search-input" 
            placeholder="搜索视频、UP主..."
            @keyup.enter="handleSearch"
          />
          <button class="bili-search-btn" @click="handleSearch">
            <el-icon><Search /></el-icon>
          </button>
        </div>

        <!-- 右侧用户区 -->
        <div class="bili-user-actions">
          <template v-if="userStore.isLoggedIn">
            <el-dropdown trigger="click" @command="handleCommand">
              <div class="bili-user-info">
                <el-avatar :src="userStore.avatar" :size="32" />
                <span class="bili-user-name">{{ userStore.nickname }}</span>
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
    <nav class="bili-nav">
      <div class="bili-nav-wrapper">
        <div 
          v-for="cat in categories" 
          :key="cat.id"
          class="bili-nav-item"
          :class="{ active: currentCategory === cat.id }"
          @click="selectCategory(cat.id)"
        >
          <el-icon><component :is="cat.icon" /></el-icon>
          <span>{{ cat.name }}</span>
        </div>
      </div>
    </nav>

    <!-- 主内容区 -->
    <main class="bili-main">
      <div class="bili-container">
        <!-- 轮播图区域 -->
        <div class="bili-banner">
          <div class="bili-banner-placeholder">
            <el-icon :size="64"><Picture /></el-icon>
            <p>轮播图区域</p>
          </div>
        </div>

        <!-- 视频网格 -->
        <div class="bili-video-section">
          <h2 class="bili-section-title">推荐视频</h2>
          <div class="bili-video-grid">
            <div 
              v-for="video in mockVideos" 
              :key="video.id"
              class="bili-video-card"
            >
              <div class="bili-video-cover">
                <div class="bili-cover-placeholder">
                  <el-icon :size="48"><VideoPlay /></el-icon>
                </div>
                <span class="bili-video-duration">{{ video.duration }}</span>
                <div class="bili-video-stats-overlay">
                  <span><el-icon><View /></el-icon> {{ video.views }}</span>
                  <span><el-icon><ChatDotRound /></el-icon> {{ video.danmaku }}</span>
                </div>
              </div>
              <div class="bili-video-info">
                <h3 class="bili-video-title">{{ video.title }}</h3>
                <div class="bili-video-meta">
                  <div class="bili-video-uploader">
                    <el-avatar :src="video.author.avatar" :size="20" />
                    <span>{{ video.author.name }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
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
  Search, User, ArrowDown, SwitchButton, VideoPlay, ChatDotRound, View,
  Star, Film, Reading, Monitor, Headset, TrophyBase, Picture
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import AuthDialog from '@/components/AuthDialog.vue'

const router = useRouter()
const userStore = useUserStore()
const searchKeyword = ref('')
const currentCategory = ref('all')
const authDialogVisible = ref(false)
const authMode = ref('login')

const categories = reactive([
  { id: 'all', name: '推荐', icon: Star },
  { id: 'video', name: '视频', icon: VideoPlay },
  { id: 'article', name: '专栏', icon: Reading },
  { id: 'live', name: '直播', icon: Monitor },
  { id: 'music', name: '音乐', icon: Headset },
  { id: 'game', name: '游戏', icon: TrophyBase }
])

const mockVideos = reactive([
  { id: 1, title: '【科普】量子计算机的工作原理详解', duration: '12:34', author: { name: 'UP主1', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '10.2万', danmaku: '1234' },
  { id: 2, title: '【教程】Vue 3 从入门到精通完整教程', duration: '45:12', author: { name: 'UP主2', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '8.5万', danmaku: '892' },
  { id: 3, title: '【科技】AI 如何改变我们的生活方式', duration: '23:45', author: { name: 'UP主3', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '15.6万', danmaku: '2341' },
  { id: 4, title: '【编程】Python 数据分析实战项目', duration: '34:56', author: { name: 'UP主4', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '6.8万', danmaku: '567' },
  { id: 5, title: '【知识】宇宙的起源与演化历程', duration: '28:30', author: { name: 'UP主5', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '12.3万', danmaku: '1567' },
  { id: 6, title: '【技术】区块链技术原理详细讲解', duration: '19:45', author: { name: 'UP主6', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '9.1万', danmaku: '734' },
  { id: 7, title: '【动画】精彩动画短片合集推荐', duration: '15:20', author: { name: 'UP主7', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '20.5万', danmaku: '3456' },
  { id: 8, title: '【音乐】经典钢琴曲演奏欣赏', duration: '08:15', author: { name: 'UP主8', avatar: 'https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png' }, views: '5.2万', danmaku: '234' }
])

onMounted(async () => {
  if (userStore.token && !userStore.userInfo) {
    try {
      await userStore.initUserInfo()
    } catch (error) {
      console.error('初始化用户信息失败:', error)
    }
  }
})

const showAuthDialog = (mode) => {
  authMode.value = mode
  authDialogVisible.value = true
}

const handleAuthSuccess = () => {
  console.log('登录注册成功')
}

const handleSearch = () => {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  console.log('搜索:', searchKeyword.value)
}

const selectCategory = (categoryId) => {
  currentCategory.value = categoryId
  console.log('选择分类:', categoryId)
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
.bili-home { min-height: 100vh; background: #f4f5f7; }

/* 顶部导航 */
.bili-header { background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.08); position: sticky; top: 0; z-index: 100; }
.bili-header-wrapper { max-width: 1400px; margin: 0 auto; padding: 0 20px; height: 64px; display: flex; align-items: center; gap: 20px; }
.bili-logo { display: flex; align-items: center; gap: 8px; cursor: pointer; flex-shrink: 0; }
.bili-logo-icon { width: 32px; height: 32px; color: var(--bili-pink); }
.bili-logo-text { font-size: 20px; font-weight: bold; background: linear-gradient(135deg, var(--bili-pink), var(--bili-blue)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.bili-search-box { flex: 1; max-width: 500px; display: flex; background: #f1f2f3; border-radius: 8px; overflow: hidden; }
.bili-search-input { flex: 1; padding: 8px 16px; border: none; background: transparent; outline: none; font-size: 14px; }
.bili-search-btn { padding: 8px 16px; border: none; background: transparent; color: #666; cursor: pointer; }
.bili-search-btn:hover { color: var(--bili-pink); }
.bili-user-actions { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.bili-user-info { display: flex; align-items: center; gap: 8px; padding: 4px 12px; border-radius: 16px; cursor: pointer; }
.bili-user-info:hover { background: #f1f2f3; }
.bili-user-name { font-size: 14px; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 分类导航 */
.bili-nav { background: #fff; border-bottom: 1px solid #e3e5e7; }
.bili-nav-wrapper { max-width: 1400px; margin: 0 auto; padding: 0 20px; display: flex; gap: 32px; }
.bili-nav-item { display: flex; align-items: center; gap: 6px; padding: 16px 0; font-size: 14px; color: #61666d; cursor: pointer; position: relative; }
.bili-nav-item:hover { color: var(--bili-pink); }
.bili-nav-item.active { color: var(--bili-pink); font-weight: 500; }
.bili-nav-item.active::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 2px; background: var(--bili-pink); }

/* 主内容 */
.bili-main { padding: 20px 0; }
.bili-container { max-width: 1400px; margin: 0 auto; padding: 0 20px; }

/* 轮播图 */
.bili-banner { margin-bottom: 24px; }
.bili-banner-placeholder { height: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; display: flex; flex-direction: column; align-items: center; justify-content: center; color: #fff; }
.bili-banner-placeholder p { margin-top: 12px; font-size: 16px; }

/* 视频区域 */
.bili-video-section { margin-bottom: 32px; }
.bili-section-title { font-size: 20px; font-weight: 600; margin-bottom: 16px; color: #18191c; }
.bili-video-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }

/* 视频卡片 */
.bili-video-card { background: #fff; border-radius: 8px; overflow: hidden; cursor: pointer; transition: all 0.3s; }
.bili-video-card:hover { transform: translateY(-4px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.bili-video-cover { position: relative; width: 100%; padding-top: 62.5%; background: #f1f2f3; overflow: hidden; }
.bili-cover-placeholder { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; color: #ccc; }
.bili-video-duration { position: absolute; bottom: 8px; right: 8px; padding: 2px 6px; background: rgba(0,0,0,0.7); color: #fff; font-size: 12px; border-radius: 4px; }
.bili-video-stats-overlay { position: absolute; top: 8px; right: 8px; display: flex; flex-direction: column; gap: 4px; }
.bili-video-stats-overlay span { display: flex; align-items: center; gap: 4px; padding: 2px 6px; background: rgba(0,0,0,0.7); color: #fff; font-size: 12px; border-radius: 4px; }
.bili-video-info { padding: 12px; }
.bili-video-title { font-size: 14px; font-weight: 500; color: #18191c; margin: 0 0 8px 0; line-height: 1.4; height: 2.8em; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.bili-video-meta { display: flex; align-items: center; justify-content: space-between; }
.bili-video-uploader { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #999; }

/* 响应式 */
@media (max-width: 1200px) { .bili-video-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 900px) { .bili-video-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { 
  .bili-video-grid { grid-template-columns: 1fr; }
  .bili-search-box { display: none; }
  .bili-user-name { display: none; }
}
</style>
