import { ref } from "vue";
import { ElMessage } from "element-plus";
import { Star, Film, Monitor, Reading } from "@element-plus/icons-vue";
import { getVideoList } from "@/api/video";
import { getCategories } from "@/api/category";
import { resolveFileUrl } from "@/utils/urlHelpers";
import { formatDuration } from "@/utils/formatters";

export function useVideoList() {
  const loading = ref(false);
  const hasMore = ref(true);
  const currentPage = ref(1);
  const pageSize = ref(20);
  const videos = ref([]);

  const currentCategory = ref(null);
  const categories = ref([]);

  const loadCategories = async () => {
    try {
      const response = await getCategories();

      let categoryList = [];
      if (response && response.data && Array.isArray(response.data)) {
        categoryList = response.data;
      } else if (Array.isArray(response)) {
        categoryList = response;
      }

      if (categoryList && categoryList.length > 0) {
        categories.value = [
          { id: null, name: "推荐", icon: Star },
          ...categoryList.map((cat) => ({
            ...cat,
            icon: Film,
          })),
        ];
      } else {
        throw new Error("分类列表为空");
      }
    } catch (error) {
      console.error("加载分类失败:", error);
      categories.value = [
        { id: null, name: "推荐", icon: Star },
        { id: 1, name: "科技", icon: Monitor },
        { id: 2, name: "教育", icon: Reading },
        { id: 3, name: "娱乐", icon: Film },
      ];
    }
  };

  const loadVideos = async (append = false) => {
    if (loading.value) return;
    loading.value = true;

    try {
      const params = {
        page: currentPage.value,
        page_size: pageSize.value,
      };

      if (currentCategory.value) {
        params.category_id = currentCategory.value;
      }

      const response = await getVideoList(params);

      if (response.success) {
        const newVideos = (response.data.items || []).map((video) => ({
          id: video.id,
          title: video.title,
          cover: resolveFileUrl(video.cover_url),
          duration: formatDuration(video.duration),
          views: video.view_count,
          likes: video.like_count || 0,
          danmaku: video.danmaku_count || 0,
          author: {
            name:
              video.uploader?.nickname ||
              video.uploader?.username ||
              "未知用户",
            avatar: resolveFileUrl(video.uploader?.avatar || ""),
            verified: false,
            verifiedType: "personal",
          },
          tags: [],
          publishTime: video.created_at,
        }));

        if (append) {
          videos.value.push(...newVideos);
        } else {
          videos.value = newVideos;
        }

        hasMore.value = videos.value.length < (response.data.total || 0);
      }
    } catch (error) {
      console.error("加载视频列表失败:", error);
      ElMessage.error("加载视频列表失败");
    } finally {
      loading.value = false;
    }
  };

  const loadMoreVideos = async () => {
    if (!hasMore.value || loading.value) return;
    currentPage.value++;
    await loadVideos(true);
  };

  const selectCategory = (categoryId) => {
    currentCategory.value = categoryId;
    currentPage.value = 1;
    loadVideos();
  };

  return {
    loading,
    hasMore,
    currentPage,
    pageSize,
    videos,
    currentCategory,
    categories,
    loadCategories,
    loadVideos,
    loadMoreVideos,
    selectCategory,
  };
}

