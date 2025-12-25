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
            <img 
              :src="userStore.avatar || '/default-avatar.png'" 
              alt="avatar" 
              class="user-avatar"
            />
            <span class="level-badge">LV.6</span>
          </div>
          
          <div class="user-info">
            <div class="name-row">
              <h1 class="nickname">{{ displayUser.nickname }}</h1>
              <span class="vip-badge" v-if="false">大会员</span>
            </div>
            
            <p class="user-bio">
              {{ displayUser.intro || "这个人很懒，什么都没有写~" }}
            </p>
            
            <div class="user-stats">
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(128) }}</span>
                <span class="stat-label">关注</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(1024) }}</span>
                <span class="stat-label">粉丝</span>
              </div>
              <div class="stat-divider"></div>
              <div class="stat-item">
                <span class="stat-value">{{ formatNumber(56789) }}</span>
                <span class="stat-label">获赞</span>
              </div>
            </div>
          </div>
          
          <div class="action-buttons">
            <el-button class="edit-btn" @click="editVisible = true">
              <span class="btn-icon">✏️</span>
              编辑资料
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
            <span class="tab-icon">🏠</span>
            <span class="tab-text">主页</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'videos' }"
            @click="activeTab = 'videos'"
          >
            <span class="tab-icon">🎬</span>
            <span class="tab-text">投稿</span>
            <span class="tab-count">{{ videos.length }}</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'favorites' }"
            @click="activeTab = 'favorites'"
          >
            <span class="tab-icon">⭐</span>
            <span class="tab-text">收藏</span>
          </div>
          <div 
            class="nav-tab"
            :class="{ active: activeTab === 'settings' }"
            @click="activeTab = 'settings'"
          >
            <span class="tab-icon">⚙️</span>
            <span class="tab-text">设置</span>
          </div>
        </div>
        
        <div class="nav-search">
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input 
              type="text" 
              placeholder="搜索视频" 
              class="search-input"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="profile-content">
      <div class="content-container">
        <!-- Left Column - Main Content -->
        <div class="content-main">
          <!-- Videos Section -->
          <section class="content-section">
            <div class="section-header">
              <h2 class="section-title">
                <span class="title-icon">🎬</span>
                我的视频
              </h2>
              <button class="more-btn">
                更多
                <span class="arrow">→</span>
              </button>
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
              <div class="empty-icon">📹</div>
              <p class="empty-text">暂无投稿视频</p>
              <el-button type="primary" @click="$router.push('/upload')">
                去投稿
              </el-button>
            </div>
          </section>
        </div>

        <!-- Right Column - Sidebar -->
        <div class="content-sidebar">
          <!-- Achievement Card -->
          <div class="sidebar-card achievement-card">
            <div class="card-header">
              <h3 class="card-title">
                <span class="title-icon">🏆</span>
                个人成就
              </h3>
            </div>
            <div class="card-body">
              <div class="achievement-item">
                <span class="achievement-label">获得点赞</span>
                <span class="achievement-value">{{ formatNumber(1234) }}</span>
              </div>
              <div class="achievement-item">
                <span class="achievement-label">获得播放</span>
                <span class="achievement-value">{{ formatNumber(56789) }}</span>
              </div>
              <div class="achievement-item">
                <span class="achievement-label">获得收藏</span>
                <span class="achievement-value">{{ formatNumber(234) }}</span>
              </div>
            </div>
          </div>

          <!-- Announcement Card -->
          <div class="sidebar-card announcement-card">
            <div class="card-header">
              <h3 class="card-title">
                <span class="title-icon">📢</span>
                公告
              </h3>
            </div>
            <div class="card-body">
              <p class="announcement-text">
                欢迎来到我的个人空间！感谢关注~
              </p>
            </div>
          </div>

          <!-- Tags Card -->
          <div class="sidebar-card tags-card">
            <div class="card-header">
              <h3 class="card-title">
                <span class="title-icon">🏷️</span>
                兴趣标签
              </h3>
            </div>
            <div class="card-body">
              <div class="tags-list">
                <span class="tag-item">科技</span>
                <span class="tag-item">游戏</span>
                <span class="tag-item">音乐</span>
                <span class="tag-item">生活</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Edit Profile Dialog -->
    <el-dialog
      v-model="editVisible"
      title="编辑资料"
      width="500px"
      destroy-on-close
      class="edit-dialog"
    >
      <div class="edit-dialog-body">
        <AvatarSection
          :avatar="userStore.avatar"
          @file-selected="handleFileSelect"
        />
        <InfoForm
          ref="infoFormRef"
          :user-info="displayUser"
          :submitting="submitting"
          @submit="handleSubmit"
        />
      </div>
    </el-dialog>

    <!-- Avatar Cropper -->
    <AvatarCropper
      v-model="cropperVisible"
      :img-src="selectedImageSrc"
      @confirm="handleCropConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useUserStore } from "@/shared/stores/user";
import { useUserActions } from "@/features/user/composables/useUserActions";
import { getVideoList } from "@/features/video/shared/api/video.api";
import type { UserInfo, Video } from "@/shared/types/entity";
import { formatNumber } from "@/shared/utils/formatters";

import AppHeader from "@/shared/components/layout/AppHeader.vue";
import VideoCard from "@/features/video/shared/components/VideoCard.vue";
import AvatarSection from "@/features/user/components/AvatarSection.vue";
import InfoForm from "@/features/user/components/InfoForm.vue";
import AvatarCropper from "@/features/user/components/AvatarCropper.vue";

const router = useRouter();
const userStore = useUserStore();
const { submitting, updateUser, uploadUserAvatar } = useUserActions();

const displayUser = reactive<UserInfo>({} as UserInfo);
const videos = ref<Video[]>([]);
const editVisible = ref(false);
const infoFormRef = ref(null);
const activeTab = ref('home');

// Avatar handling
const cropperVisible = ref(false);
const selectedImageSrc = ref("");

// Initialize
onMounted(async () => {
  await userStore.fetchUserInfo();
  Object.assign(displayUser, userStore.userInfo);
  loadMyVideos();
});

// Load user's videos
const loadMyVideos = async () => {
  const res = await getVideoList({ page: 1, page_size: 8 });
  if (res.success && res.data?.items) {
    videos.value = res.data.items;
  }
};

const handleVideoClick = (v: Video) => router.push(`/videos/${v.id}`);

// Edit profile handlers
const handleFileSelect = (file: File) => {
  const reader = new FileReader();
  reader.onload = (e) => {
    selectedImageSrc.value = e.target?.result as string;
    cropperVisible.value = true;
  };
  reader.readAsDataURL(file);
};

const handleCropConfirm = async (file: File) => {
  const success = await uploadUserAvatar(file);
  if (success) Object.assign(displayUser, userStore.userInfo);
};

const handleSubmit = async (data: any) => {
  const success = await updateUser(data);
  if (success) {
    Object.assign(displayUser, userStore.userInfo);
    editVisible.value = false;
  }
};
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
    url("https://cdn.pixabay.com/photo/2016/11/21/14/53/man-1845814_1280.jpg");
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
  width: 96px;
  height: 96px;
  border-radius: var(--radius-circle);
  border: 4px solid rgba(255, 255, 255, 0.9);
  object-fit: cover;
  box-shadow: var(--shadow-lg);
  transform: translateY(24px);
  background: var(--bg-white);
}

.level-badge {
  position: absolute;
  bottom: 20px;
  right: -4px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  color: var(--text-white);
  background: linear-gradient(135deg, #FF9500 0%, #FF5E3A 100%);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-sm);
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

.vip-badge {
  padding: 2px 8px;
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  color: #FFD700;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid #FFD700;
  border-radius: var(--radius-sm);
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

.edit-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.4);
  color: var(--text-white);
  border-radius: var(--radius-round);
  backdrop-filter: blur(8px);
  transition: all var(--transition-base);

  .btn-icon {
    font-style: normal;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.6);
    transform: translateY(-1px);
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

.nav-search {
  flex-shrink: 0;
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--bg-gray-1);
  border-radius: var(--radius-round);
  transition: all var(--transition-base);

  &:focus-within {
    background: var(--bg-white);
    box-shadow: 0 0 0 2px var(--primary-light);
  }
}

.search-icon {
  font-style: normal;
  font-size: var(--font-size-sm);
  opacity: 0.5;
}

.search-input {
  width: 120px;
  border: none;
  background: transparent;
  font-size: var(--font-size-sm);
  color: var(--text-primary);
  outline: none;

  &::placeholder {
    color: var(--text-tertiary);
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

/* Main Column */
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
  align-items: center;
  justify-content: space-between;
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

.more-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  background: var(--bg-gray-1);
  border: none;
  border-radius: var(--radius-round);
  cursor: pointer;
  transition: all var(--transition-base);

  .arrow {
    transition: transform var(--transition-base);
  }

  &:hover {
    color: var(--primary-color);
    background: var(--primary-light);

    .arrow {
      transform: translateX(2px);
    }
  }
}

.video-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

/* Empty State */
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

/* Sidebar */
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

/* Achievement Card */
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

/* Announcement Card */
.announcement-text {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: var(--line-height-relaxed);
  margin: 0;
}

/* Tags Card */
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag-item {
  padding: var(--space-1) var(--space-3);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);
  background: var(--bg-gray-1);
  border-radius: var(--radius-round);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    color: var(--primary-color);
    background: var(--primary-light);
  }
}

/* Edit Dialog */
.edit-dialog-body {
  padding: 0 var(--space-4);
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
