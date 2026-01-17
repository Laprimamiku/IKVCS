<template>
  <div class="bili-profile-space">
    <AppHeader />

    <!-- Banner Section -->
    <div class="profile-banner">
      <div class="banner-bg"></div>
      <div class="banner-overlay"></div>
      
      <div class="banner-content">
        <!-- User Card -->
        <div class="user-card">
          <div class="avatar-wrapper">
            <el-avatar 
              :src="displayAvatar" 
              :size="96"
              class="user-avatar"
              :fit="'cover'"
            >
              <el-icon :size="48"><UserFilled /></el-icon>
            </el-avatar>
          </div>
          
          <div class="user-info">
            <div class="name-row">
              <h1 class="nickname">{{ userInfo.nickname }}</h1>
            </div>
            
            <p class="user-bio">
              {{ userInfo.intro || "这个人很懒，什么都没有写~" }}
            </p>
            
            <div class="user-stats">
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(profileData.following_count) }}</span>
                <span class="stat-label">关注</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(profileData.followers_count) }}</span>
                <span class="stat-label">粉丝</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(totalLikes) }}</span>
                <span class="stat-label">获赞</span>
              </div>
            </div>
          </div>
          
          <div class="action-buttons" v-if="shouldShowFollowButton">
            <el-button 
              :type="profileData.is_following ? 'info' : 'primary'"
              class="follow-btn"
              @click="handleFollowToggle"
              :loading="followLoading"
            >
              <el-icon v-if="!profileData.is_following" class="btn-icon"><Plus /></el-icon>
              {{ profileData.is_following ? '已关注' : '关注' }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="profile-nav">
      <div class="nav-container">
        <div class="nav-tabs">
          <div 
            class="nav-tab" 
            :class="{ active: activeTab === 'home' }"
            @click="activeTab = 'home'"
          >
            <el-icon class="tab-icon"><HomeFilled /></el-icon>
            <span class="tab-text">主页</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'videos' }"
            @click="activeTab = 'videos'"
          >
            <el-icon class="tab-icon"><VideoCamera /></el-icon>
            <span class="tab-text">投稿</span>
            <span class="tab-count">{{ videos.length }}</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'favorites' }"
            @click="activeTab = 'favorites'"
          >
            <el-icon class="tab-icon"><Star /></el-icon>
            <span class="tab-text">收藏</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Profile Visibility Notice -->
    <div v-if="!profileVisible" class="profile-visibility-notice">
      <el-alert
        type="info"
        :closable="false"
        show-icon
      >
        <template #title>
          <span>该用户已设置主页为隐藏状态</span>
        </template>
      </el-alert>
    </div>

    <!-- Main Content -->
    <div class="profile-content">
      <div class="content-container">
        <!-- Left Column - Main Content -->
        <div class="content-main">
          <!-- Home Tab -->
          <section v-if="activeTab === 'home'" class="content-section">
            <!-- 投稿栏目 -->
            <div class="home-section">
              <div class="section-header">
                <h3 class="section-title">
                  <el-icon class="title-icon"><VideoCamera /></el-icon>
                  投稿
                </h3>
                <el-button type="primary" link @click="activeTab = 'videos'">
                  查看更多
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
              <div class="video-grid" v-if="homeVideos.length > 0">
                <VideoCard
                  v-for="video in homeVideos"
                  :key="video.id"
                  :video="video"
                  @click="handleVideoClick"
                />
              </div>
              <el-empty v-else description="暂无投稿视频" :image-size="80" />
            </div>

            <!-- 分隔线 -->
            <div class="home-section-divider"></div>

            <!-- 收藏栏目 -->
            <div class="home-section">
              <div class="section-header">
                <h3 class="section-title">
                  <el-icon class="title-icon"><Star /></el-icon>
                  收藏
                </h3>
                <el-button type="primary" link @click="activeTab = 'favorites'">
                  查看更多
                  <el-icon><ArrowRight /></el-icon>
                </el-button>
              </div>
              <div class="video-grid" v-if="homeCollections.length > 0">
                <VideoCard
                  v-for="video in homeCollections"
                  :key="video.id"
                  :video="video"
                  @click="handleVideoClick"
                />
              </div>
              <el-empty v-else description="暂无收藏视频" :image-size="80" />
            </div>
          </section>

          <!-- Videos Tab (投稿) -->
          <section v-if="activeTab === 'videos'" class="content-section">
            <div class="section-header">
              <h2 class="section-title">
                <el-icon class="title-icon"><VideoCamera /></el-icon>
                投稿
              </h2>
            </div>

            <div class="video-grid" v-if="videos.length > 0">
              <VideoCard
                v-for="video in videos"
                :key="video.id"
                :video="video"
                @click="handleVideoClick"
              />
            </div>
            
            <div v-else class="empty-state">
              <el-icon class="empty-icon" :size="48"><VideoCamera /></el-icon>
              <p class="empty-text">暂无投稿视频</p>
            </div>
          </section>

          <!-- Collections Tab (收藏) -->
          <section v-if="activeTab === 'favorites'" class="content-section">
            <div class="section-header">
              <h2 class="section-title">
                <el-icon class="title-icon"><Star /></el-icon>
                收藏
              </h2>
            </div>

            <div class="video-grid" v-if="collections.length > 0">
              <VideoCard
                v-for="video in collections"
                :key="video.id"
                :video="video"
                @click="handleVideoClick"
              />
            </div>
            
            <div v-else class="empty-state">
              <el-icon class="empty-icon" :size="48"><Star /></el-icon>
              <p class="empty-text">暂无收藏视频</p>
            </div>
          </section>
        </div>

        <!-- Right Column - Sidebar -->
        <div class="content-sidebar">
          <!-- Achievement Card -->
          <div class="sidebar-card achievement-card">
            <div class="card-header">
              <h3 class="card-title">
                <el-icon class="title-icon"><Trophy /></el-icon>
                个人成就
              </h3>
            </div>
            <div class="card-body">
              <div class="achievement-item">
                <span class="achievement-label">获得点赞</span>
                <span class="achievement-value">{{ formatNumber(totalLikes) }}</span>
              </div>
              <div class="achievement-item">
                <span class="achievement-label">获得播放</span>
                <span class="achievement-value">{{ formatNumber(totalViews) }}</span>
              </div>
              <div class="achievement-item">
                <span class="achievement-label">获得收藏</span>
                <span class="achievement-value">{{ formatNumber(totalCollections) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { useRouter, useRoute } from "vue-router";
import { HomeFilled, VideoCamera, Trophy, ArrowRight, Star, Clock, UserFilled, Plus } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useUserStore } from "@/shared/stores/user";
import { getUserById, type UserProfileData, followUser, unfollowUser } from "@/features/user/api/user.api";
import { getUserVideos, getUserCollections } from "@/features/video/shared/api/video.api";
import type { UserInfo, Video } from "@/shared/types/entity";
import { formatNumber } from "@/shared/utils/formatters";

import AppHeader from "@/shared/components/layout/AppHeader.vue";
import VideoCard from "@/features/video/shared/components/VideoCard.vue";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();

const userId = computed(() => parseInt(route.params.id as string));
const userInfo = reactive<UserInfo>({} as UserInfo);
const profileData = reactive<UserProfileData>({
  user: {} as UserInfo,
  following_count: 0,
  followers_count: 0,
  is_following: false
});
const videos = ref<Video[]>([]);
const collections = ref<Video[]>([]);
const watchHistory = ref<Video[]>([]);
const activeTab = ref('home');
const followLoading = ref(false);
const profileVisible = ref(true); // 主页是否公开

// 主页展示数据（前4个）
const homeVideos = computed(() => videos.value.slice(0, 4));
const homeCollections = computed(() => collections.value.slice(0, 4));
const homeHistory = computed(() => watchHistory.value.slice(0, 4));

// 头像显示
const displayAvatar = computed(() => {
  if (userInfo.avatar) {
    return userInfo.avatar;
  }
  return undefined; // el-avatar 会在 src 为 undefined 时显示默认图标
});

// 是否显示关注按钮
const shouldShowFollowButton = computed(() => {
  // 必须已登录
  if (!userStore.isAuthenticated || !userStore.userInfo?.id) {
    return false;
  }
  // 必须有目标用户信息
  if (!userInfo.id) {
    return false;
  }
  // 不能是自己
  return userInfo.id !== userStore.userInfo.id;
});

// 统计数据
const totalLikes = computed(() => videos.value.reduce((sum, v) => sum + (v.like_count || 0), 0));
const totalViews = computed(() => videos.value.reduce((sum, v) => sum + (v.view_count || 0), 0));
const totalCollections = computed(() => videos.value.reduce((sum, v) => sum + (v.collect_count || 0), 0));

// Initialize
onMounted(async () => {
  await loadUserProfile();
  if (profileVisible.value) {
    await loadUserVideos();
    await loadUserCollections();
    await loadUserWatchHistory();
  }
});

// Load user profile
const loadUserProfile = async () => {
  try {
    const res = await getUserById(userId.value);
    if (res.success && res.data) {
      Object.assign(userInfo, res.data.user);
      Object.assign(profileData, res.data);
      // 检查主页是否公开（profile_visible 字段，默认为 true）
      profileVisible.value = res.data.profile_visible !== false;
    }
  } catch (error) {
    console.error('加载用户信息失败:', error);
    ElMessage.error('加载用户信息失败');
  }
};

// Load user videos
const loadUserVideos = async () => {
  try {
    const res = await getUserVideos(userId.value, { page: 1, page_size: 100 });
    if (res.success && res.data?.items) {
      videos.value = res.data.items;
    }
  } catch (error) {
    console.error('加载用户视频失败:', error);
  }
};

// Load user collections
const loadUserCollections = async () => {
  try {
    const res = await getUserCollections(userId.value, { page: 1, page_size: 100 });
    if (res.success && res.data?.items) {
      collections.value = res.data.items;
    }
  } catch (error) {
    console.error('加载用户收藏失败:', error);
  }
};

// Load user watch history
const loadUserWatchHistory = async () => {
  // 注意：观看历史通常是私密的，这里暂时不实现，或者需要后端提供公开的观看历史API
  // 如果后端不支持，可以留空或显示提示
  watchHistory.value = [];
};

// Handle follow toggle
const handleFollowToggle = async () => {
  if (!userStore.isAuthenticated) {
    ElMessage.warning('请先登录');
    return;
  }
  
  followLoading.value = true;
  try {
    if (profileData.is_following) {
      // 取关
      const res = await unfollowUser(userId.value);
      if (res.success) {
        profileData.is_following = false;
        profileData.followers_count = Math.max(0, profileData.followers_count - 1);
        ElMessage.success('取消关注成功');
      }
    } else {
      // 关注
      const res = await followUser(userId.value);
      if (res.success) {
        profileData.is_following = true;
        profileData.followers_count += 1;
        ElMessage.success('关注成功');
      }
    }
  } catch (error: any) {
    console.error('关注操作失败:', error);
    ElMessage.error(error.response?.data?.detail || '操作失败');
  } finally {
    followLoading.value = false;
  }
};

const handleVideoClick = (v: Video) => router.push(`/videos/${v.id}`);
</script>

<style lang="scss" scoped>
.bili-profile-space {
  min-height: 100vh;
  background: var(--bg-global);
}

/* Banner Section */
.profile-banner {
  position: relative;
  height: 280px;
  overflow: hidden;
}

.banner-bg {
  position: absolute;
  inset: 0;
  background: 
    linear-gradient(135deg, #667eea 0%, #764ba2 100%),
    url(var(--profile-bg-url, '/default-profile-bg.jpg'));
  background-size: cover;
  background-position: center;
  filter: blur(0);
}

.banner-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.1) 0%,
    rgba(0, 0, 0, 0.5) 100%
  );
}

.banner-content {
  position: relative;
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding);
  height: 100%;
  display: flex;
  align-items: flex-end;
  padding-bottom: var(--space-6);
}

/* User Card */
.user-card {
  display: flex;
  align-items: flex-end;
  gap: var(--space-6);
  width: 100%;
}

.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.user-avatar {
  border: 4px solid rgba(255, 255, 255, 0.9);
  box-shadow: var(--shadow-lg);
  transform: translateY(24px);
  background: var(--bg-white);
}

.user-info {
  flex: 1;
  color: var(--text-white);
  padding-bottom: var(--space-2);
}

.name-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.nickname {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  margin: 0;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.user-bio {
  font-size: var(--font-size-sm);
  opacity: 0.9;
  margin: 0 0 var(--space-3);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  max-width: 400px;
}

.user-stats {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-bold);
}

.stat-label {
  font-size: var(--font-size-xs);
  opacity: 0.8;
}

.stat-divider {
  width: 1px;
  height: 24px;
  background: rgba(255, 255, 255, 0.3);
}

.action-buttons {
  flex-shrink: 0;
  padding-bottom: var(--space-2);
}

.follow-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-round);
  backdrop-filter: blur(8px);
  transition: all var(--transition-base);
  font-weight: var(--font-weight-medium);
  
  .btn-icon {
    font-size: var(--font-size-base);
  }
  
  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
  
  &[type="info"] {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
    color: var(--text-white);
    
    &:hover {
      background: rgba(255, 255, 255, 0.3);
      border-color: rgba(255, 255, 255, 0.4);
    }
  }
}

/* Navigation */
.profile-nav {
  background: var(--bg-white);
  border-bottom: 1px solid var(--border-light);
  position: sticky;
  top: var(--header-height);
  z-index: var(--z-sticky);
}

.nav-container {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: 0 var(--content-padding);
  padding-left: calc(var(--content-padding) + 120px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
}

.nav-tabs {
  display: flex;
  gap: var(--space-1);
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  font-size: var(--font-size-base);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  position: relative;

  .tab-icon {
    font-style: normal;
    font-size: var(--font-size-lg);
  }

  .tab-count {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
    margin-left: var(--space-1);
  }

  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }

  &.active {
    color: var(--primary-color);
    font-weight: var(--font-weight-medium);

    &::after {
      content: '';
      position: absolute;
      bottom: -8px;
      left: 50%;
      transform: translateX(-50%);
      width: 24px;
      height: 3px;
      background: var(--primary-color);
      border-radius: var(--radius-round);
    }
  }
}

/* Main Content */
.profile-content {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: var(--space-6) var(--content-padding);
}

.content-container {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--space-6);
}

.content-main {
  min-width: 0;
}

.content-section {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;

  .title-icon {
    font-style: normal;
  }
}

.home-section {
  margin-bottom: var(--space-6);
  
  &:last-child {
    margin-bottom: 0;
  }
  
  .section-header {
    margin-bottom: var(--space-4);
  }
  
  .section-title {
    font-size: var(--font-size-lg);
    font-weight: var(--font-weight-semibold);
  }
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) 0;
  color: var(--text-tertiary);

  .empty-icon {
    font-size: 48px;
    margin-bottom: var(--space-4);
    opacity: 0.5;
  }

  .empty-text {
    font-size: var(--font-size-base);
    margin: 0 0 var(--space-4);
  }
}

.content-sidebar {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.sidebar-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.card-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border-light);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  margin: 0;

  .title-icon {
    font-style: normal;
  }
}

.card-body {
  padding: var(--space-4);
}

.achievement-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;

  &:not(:last-child) {
    border-bottom: 1px solid var(--border-light);
  }
}

.achievement-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.achievement-value {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--primary-color);
}

/* Responsive */
@media (max-width: 1200px) {
  .content-container {
    grid-template-columns: 1fr 280px;
  }

  .video-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 992px) {
  .content-container {
    grid-template-columns: 1fr;
  }

  .content-sidebar {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
  }

  .video-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 768px) {
  .nav-container {
    padding-left: var(--content-padding);
  }

  .video-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .content-sidebar {
    grid-template-columns: 1fr;
  }

  .user-card {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .user-avatar {
    transform: translateY(0);
  }
}

.profile-visibility-notice {
  max-width: var(--container-max-width);
  margin: 0 auto;
  padding: var(--space-4) var(--content-padding);
}

.home-section-divider {
  height: 1px;
  background: var(--border-light);
  margin: var(--space-6) 0;

  .user-info {
    padding-bottom: 0;
  }

  .user-bio {
    max-width: none;
  }

  .action-buttons {
    padding-bottom: 0;
  }
}
</style>

