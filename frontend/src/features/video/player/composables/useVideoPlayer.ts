import { ref, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { getVideoDetail, incrementViewCount, getVideoList } from "@/features/video/shared/api/video.api";
import type { Video, RecommendVideo } from "@/shared/types/entity";

export function useVideoPlayer() {
  const route = useRoute();
  const router = useRouter();

  const videoData = ref<Video | null>(null);
  const recommendVideos = ref<RecommendVideo[]>([]);
  const loading = ref(true);

  const videoIdRef = computed(() => {
    const id = route.params.id;
    return Array.isArray(id) ? parseInt(id[0]) : parseInt(id || '0');
  });

  const loadVideoDetail = async () => {
    loading.value = true;
    const id = videoIdRef.value;
    if (!id) {
      router.push('/');
      return;
    }

    try {
      const res = await getVideoDetail(id);
      if (res.success) {
        videoData.value = res.data;
        await loadRecommendVideos();
        await incrementViewCount(id);

        // 转码轮询
        if (videoData.value && (videoData.value.status === 0 || !videoData.value.video_url)) {
          pollTranscodingStatus(id);
        }
      } else {
        ElMessage.error('视频不存在或已被删除');
        router.push('/');
      }
    } catch (error) {
      console.error('加载视频失败:', error);
      ElMessage.error('加载视频失败');
    } finally {
      loading.value = false;
    }
  };

  const loadRecommendVideos = async () => {
    if (!videoData.value) return;

    try {
      const res = await getVideoList({
        page: 1,
        page_size: 10,
        category_id: videoData.value.category_id,
      });

      if (res.success && res.data) {
        recommendVideos.value = res.data.items
          .filter((v) => v.id !== videoData.value?.id)
          .slice(0, 10)
          .map((v) => ({
            id: v.id,
            title: v.title,
            cover: v.cover_url,
            uploader: v.uploader?.nickname || v.uploader?.username || '未知',
            views: v.view_count || 0,
          }));
      }
    } catch (error) {
      console.error('加载推荐视频失败:', error);
    }
  };

  const pollTranscodingStatus = async (videoId: number) => {
    let attempts = 0;
    const maxAttempts = 60;
    const pollInterval = 2000;

    const poll = setInterval(async () => {
      attempts++;
      if (attempts > maxAttempts) {
        clearInterval(poll);
        return;
      }

      try {
        const res = await getVideoDetail(videoId);
        if (res.success && res.data.video_url) {
          videoData.value = res.data;
          ElMessage.success('视频转码完成');
          clearInterval(poll);
        }
      } catch (error) {
        console.error('轮询转码状态失败:', error);
      }
    }, pollInterval);
  };

  watch(
    () => route.params.id,
    (newId) => {
      if (newId) {
        videoData.value = null;
        loadVideoDetail();
      }
    },
    { immediate: true }
  );

  return {
    videoData,
    recommendVideos,
    loading,
    videoIdRef,
    loadVideoDetail,
  };
}
